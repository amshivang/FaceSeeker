// ponytail: clean MainViewModel coordinating scan lifecycle, collections, and events
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using FaceSeeker.GUI.Models;
using FaceSeeker.GUI.Services;
using FaceSeeker.GUI.Views;
using Microsoft.Win32;

namespace FaceSeeker.GUI.ViewModels
{
    public partial class MainViewModel : ObservableObject
    {
        [ObservableProperty]
        private bool _isScanning;

        [ObservableProperty]
        private string _statusText = "Ready";

        [ObservableProperty]
        private int _progressValue;

        [ObservableProperty]
        private int _progressMax = 100;

        [ObservableProperty]
        private string _progressPct = "0%";

        [ObservableProperty]
        private string _currentVideo = string.Empty;

        public ObservableCollection<string> VideoFiles { get; } = new();
        public ObservableCollection<TargetFaceItem> TargetFaces { get; } = new();
        public ObservableCollection<MatchResultViewModel> Results { get; } = new();

        private PythonBridge? _bridge;
        private CancellationTokenSource? _cts;
        private bool _isCancelling;
        private AppSettings _settings = AppSettings.Load();
        private readonly ConcurrentDictionary<string, double> _dedupeTracker = new();
        private readonly ExportService _exportService = new();

        // FIX: PERFORMANCE-04 — High-frequency match batching queue & timer
        private readonly ConcurrentQueue<MatchResultViewModel> _matchBuffer = new();
        private readonly DispatcherTimer _batchTimer;

        public MainViewModel()
        {
            _batchTimer = new DispatcherTimer(DispatcherPriority.Background)
            {
                Interval = TimeSpan.FromMilliseconds(60)
            };
            _batchTimer.Tick += OnBatchTimerTick;
            _batchTimer.Start();
        }

        private void OnBatchTimerTick(object? sender, EventArgs e)
        {
            if (_matchBuffer.IsEmpty) return;

            int count = 0;
            // Drain up to 25 matches per frame tick to prevent UI locking
            while (count < 25 && _matchBuffer.TryDequeue(out var vm))
            {
                Results.Add(vm);
                count++;
            }
        }

        [RelayCommand]
        public void AddVideos()
        {
            var dlg = new OpenFileDialog
            {
                Multiselect = true,
                Title = "Select Videos to Scan",
                Filter = "Video Files (*.mp4;*.avi;*.mkv;*.mov;*.wmv)|*.mp4;*.avi;*.mkv;*.mov;*.wmv|All Files (*.*)|*.*"
            };

            if (!string.IsNullOrEmpty(_settings.LastVideoFolder) && Directory.Exists(_settings.LastVideoFolder))
            {
                dlg.InitialDirectory = _settings.LastVideoFolder;
            }

            if (dlg.ShowDialog(Application.Current?.MainWindow) == true)
            {
                foreach (var file in dlg.FileNames)
                {
                    if (!VideoFiles.Contains(file))
                    {
                        VideoFiles.Add(file);
                    }
                }
                if (dlg.FileNames.Length > 0)
                {
                    _settings.LastVideoFolder = Path.GetDirectoryName(dlg.FileNames[0]) ?? "";
                    _settings.Save();
                }
            }
        }

        [RelayCommand]
        public void RemoveVideo(string? path)
        {
            if (!string.IsNullOrEmpty(path))
            {
                VideoFiles.Remove(path);
            }
        }

        [RelayCommand]
        public void AddTargetFace()
        {
            var dlg = new OpenFileDialog
            {
                Title = "Select Target Face Photo",
                Filter = "Image Files (*.jpg;*.jpeg;*.png;*.bmp)|*.jpg;*.jpeg;*.png;*.bmp|All Files (*.*)|*.*"
            };

            if (dlg.ShowDialog(Application.Current?.MainWindow) == true)
            {
                string defaultName = Path.GetFileNameWithoutExtension(dlg.FileName);
                var inputDlg = new NameInputDialog(defaultName);
                // FIX: UX-02 — Modal dialog ownership
                inputDlg.Owner = Application.Current?.MainWindow;
                if (inputDlg.ShowDialog() == true && !string.IsNullOrWhiteSpace(inputDlg.EnteredName))
                {
                    try
                    {
                        var item = TargetFaceItem.FromFile(inputDlg.EnteredName.Trim(), dlg.FileName);
                        TargetFaces.Add(item);
                        StatusText = $"Added target: {item.PersonName}";
                    }
                    catch (Exception ex)
                    {
                        MessageBox.Show($"Failed to load image: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                    }
                }
            }
        }

        [RelayCommand]
        public void RemoveTarget(TargetFaceItem? item)
        {
            if (item != null)
            {
                TargetFaces.Remove(item);
            }
        }

        [RelayCommand]
        public async Task StartScanAsync()
        {
            if (TargetFaces.Count == 0)
            {
                MessageBox.Show("Please register at least one target face first.", "No Target Faces", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            if (VideoFiles.Count == 0)
            {
                MessageBox.Show("Please add at least one video to scan.", "No Videos", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            _settings = AppSettings.Load();
            Results.Clear();
            _dedupeTracker.Clear();
            while (_matchBuffer.TryDequeue(out _)) { }
            ProgressValue = 0;
            ProgressPct = "0%";
            IsScanning = true;
            _isCancelling = false;
            StatusText = "Connecting to Python Engine...";

            _cts = new CancellationTokenSource();

            try
            {
                if (_bridge == null || !_bridge.IsConnected)
                {
                    _bridge?.Dispose();
                    _bridge = new PythonBridge();

                    _bridge.OnMatch += OnMatchReceived;
                    _bridge.OnProgress += OnProgressReceived;
                    _bridge.OnVideoDone += OnVideoDoneReceived;
                    _bridge.OnRegisterResult += OnRegisterResultReceived;
                    _bridge.OnScanComplete += OnScanCompleteReceived;
                    _bridge.OnError += OnErrorReceived;

                    await _bridge.StartAsync(_settings.ServerPort);
                }

                StatusText = "Registering targets...";
                await _bridge.SendCommandAsync(new SimpleCommand("clear_targets"));

                // FIX: CORRECTNESS-03 — Validate target registration
                int registeredCount = 0;
                foreach (var target in TargetFaces)
                {
                    await _bridge.SendCommandAsync(new RegisterRequest
                    {
                        Cmd = "register_target",
                        Name = target.PersonName,
                        ImageB64 = target.ImageB64
                    });
                    registeredCount++;
                }

                StatusText = $"Enrolled {registeredCount} targets. Starting scan...";
                var scanReq = new ScanRequest
                {
                    Cmd = "scan",
                    Videos = VideoFiles.ToList(),
                    FrameSkip = _settings.FrameSkip,
                    CosineThreshold = _settings.CosineThreshold
                };

                await _bridge.SendCommandAsync(scanReq);
            }
            catch (Exception ex)
            {
                IsScanning = false;
                StatusText = $"Engine start error: {ex.Message}";
                MessageBox.Show($"Could not start Python engine:\n{ex.Message}", "Engine Error", MessageBoxButton.OK, MessageBoxImage.Error);
                _bridge?.Dispose();
                _bridge = null;
            }
        }

        [RelayCommand]
        public async Task CancelScanAsync()
        {
            if (!IsScanning) return;
            _isCancelling = true;
            StatusText = "Cancelling scan...";

            try
            {
                if (_bridge != null)
                {
                    await _bridge.SendCommandAsync(new SimpleCommand("cancel"));
                }
                _cts?.Cancel();
            }
            catch { }

            // LEAK-09: If engine doesn't respond within 2s, force kill it
            _ = Task.Run(async () =>
            {
                await Task.Delay(2000);
                if (_bridge != null)
                {
                    _bridge.Dispose();
                    _bridge = null;
                }
            });

            IsScanning = false;
            StatusText = "Scan cancelled.";
        }

        [RelayCommand]
        public void OpenSettings()
        {
            var win = new SettingsWindow(_settings);
            // FIX: UX-02 — Modal dialog ownership
            win.Owner = Application.Current?.MainWindow;
            if (win.ShowDialog() == true)
            {
                _settings = AppSettings.Load();
            }
        }

        // BUG-02 FIX: Drag-and-drop handlers for DropZone controls
        [RelayCommand]
        public void HandleImageDrop(object? param)
        {
            var files = param switch
            {
                List<string> list => list,
                string[] arr => arr.ToList(),
                string s => new List<string> { s },
                _ => null
            };

            if (files == null || files.Count == 0) return;

            foreach (var file in files)
            {
                string ext = Path.GetExtension(file).ToLowerInvariant();
                if (ext is ".jpg" or ".jpeg" or ".png" or ".bmp")
                {
                    string defaultName = Path.GetFileNameWithoutExtension(file);
                    var inputDlg = new NameInputDialog(defaultName);
                    // FIX: UX-02 — Modal dialog ownership
                    inputDlg.Owner = Application.Current?.MainWindow;
                    if (inputDlg.ShowDialog() == true && !string.IsNullOrWhiteSpace(inputDlg.EnteredName))
                    {
                        try
                        {
                            var item = TargetFaceItem.FromFile(inputDlg.EnteredName.Trim(), file);
                            TargetFaces.Add(item);
                            StatusText = $"Added target: {item.PersonName}";
                        }
                        catch (Exception ex)
                        {
                            MessageBox.Show($"Failed to load image: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                        }
                    }
                }
            }
        }

        [RelayCommand]
        public void HandleVideoDrop(object? param)
        {
            var files = param switch
            {
                List<string> list => list,
                string[] arr => arr.ToList(),
                string s => new List<string> { s },
                _ => null
            };

            if (files == null || files.Count == 0) return;

            foreach (var file in files)
            {
                string ext = Path.GetExtension(file).ToLowerInvariant();
                if (ext is ".mp4" or ".avi" or ".mkv" or ".mov" or ".wmv")
                {
                    if (!VideoFiles.Contains(file))
                    {
                        VideoFiles.Add(file);
                    }
                }
            }
        }

        [RelayCommand]
        public void Export()
        {
            if (Results.Count == 0)
            {
                MessageBox.Show("No match results to export.", "Empty Results", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            var dlg = new SaveFileDialog
            {
                Title = "Export Match Results",
                Filter = "CSV File (*.csv)|*.csv|JSON File (*.json)|*.json|Summary Report (*.txt)|*.txt",
                FileName = $"FaceSeeker_Export_{DateTime.Now:yyyyMMdd_HHmmss}"
            };

            if (!string.IsNullOrEmpty(_settings.LastExportFolder) && Directory.Exists(_settings.LastExportFolder))
            {
                dlg.InitialDirectory = _settings.LastExportFolder;
            }

            if (dlg.ShowDialog(Application.Current?.MainWindow) == true)
            {
                try
                {
                    string ext = Path.GetExtension(dlg.FileName).ToLowerInvariant();
                    if (ext == ".json")
                    {
                        _exportService.ExportJson(Results, dlg.FileName);
                    }
                    else if (ext == ".txt")
                    {
                        _exportService.ExportTxtReport(Results, dlg.FileName);
                    }
                    else
                    {
                        _exportService.ExportCsv(Results, dlg.FileName);
                    }

                    _settings.LastExportFolder = Path.GetDirectoryName(dlg.FileName) ?? "";
                    _settings.Save();

                    StatusText = $"Exported {Results.Count} results to {Path.GetFileName(dlg.FileName)}";
                    MessageBox.Show($"Results exported successfully to:\n{dlg.FileName}", "Export Complete", MessageBoxButton.OK, MessageBoxImage.Information);
                }
                catch (Exception ex)
                {
                    MessageBox.Show($"Export failed: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
        }

        [RelayCommand]
        public void ClearResults()
        {
            Results.Clear();
            _dedupeTracker.Clear();
            while (_matchBuffer.TryDequeue(out _)) { }
            StatusText = "Results cleared.";
        }

        private void OnMatchReceived(MatchMessage match)
        {
            // Parse seconds from timestamp for deduplication
            double seconds = 0;
            if (TimeSpan.TryParse(match.TimestampStr, System.Globalization.CultureInfo.InvariantCulture, out var ts))
            {
                seconds = ts.TotalSeconds;
            }
            else
            {
                seconds = match.FrameNumber;
            }

            string dedupeKey = $"{match.TargetName}|{match.VideoPath}";
            if (_dedupeTracker.TryGetValue(dedupeKey, out var lastTime))
            {
                if (Math.Abs(seconds - lastTime) < _settings.DuplicateSuppressSeconds)
                {
                    return; // Skip duplicate detection within suppress window
                }
            }
            _dedupeTracker[dedupeKey] = seconds;

            var vm = new MatchResultViewModel(match);
            // Enqueue into high-performance buffer drained by DispatcherTimer
            _matchBuffer.Enqueue(vm);
        }

        private void OnProgressReceived(ProgressMessage progress)
        {
            Application.Current?.Dispatcher.InvokeAsync(() =>
            {
                CurrentVideo = Path.GetFileName(progress.Video);
                ProgressMax = Math.Max(1, progress.Total);
                ProgressValue = progress.Current;
                int pct = (int)((progress.Current / (double)ProgressMax) * 100);
                ProgressPct = $"{pct}%";
                StatusText = $"Scanning {CurrentVideo}: frame {progress.Current}/{progress.Total} ({ProgressPct})";
            });
        }

        private void OnVideoDoneReceived(VideoDoneMessage done)
        {
            Application.Current?.Dispatcher.InvokeAsync(() =>
            {
                string name = Path.GetFileName(done.VideoPath);
                if (!string.IsNullOrEmpty(done.Error))
                {
                    StatusText = $"Finished {name} with error: {done.Error}";
                }
                else
                {
                    StatusText = $"Finished {name}: {done.TotalMatches} matches found";
                }
            });
        }

        private void OnScanCompleteReceived()
        {
            Application.Current?.Dispatcher.InvokeAsync(() =>
            {
                // Drain any residual matches in queue
                while (_matchBuffer.TryDequeue(out var vm))
                {
                    Results.Add(vm);
                }
                IsScanning = false;
                if (!_isCancelling)
                {
                    StatusText = $"Scan complete! Total matches: {Results.Count}";
                }
            });
        }

        private void OnErrorReceived(string error)
        {
            Application.Current?.Dispatcher.InvokeAsync(() =>
            {
                IsScanning = false;
                StatusText = $"Error: {error}";
            });
        }

        private void OnRegisterResultReceived(RegisterResultMessage reg)
        {
            if (!reg.Success)
            {
                Application.Current?.Dispatcher.InvokeAsync(() =>
                {
                    StatusText = $"Notice: Failed to enroll target '{reg.Name}': {reg.Error}";
                });
            }
        }
    }
}