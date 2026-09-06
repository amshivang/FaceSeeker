// ponytail: clean process manager and socket event dispatcher using System.Text.Json
using System;
using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using FaceSeeker.GUI.Models;

namespace FaceSeeker.GUI.Services
{
    public class PythonBridge : IDisposable
    {
        private Process? _process;
        private readonly SocketClient _socketClient = new();
        private bool _disposed;

        public event Action<MatchMessage>? OnMatch;
        public event Action<ProgressMessage>? OnProgress;
        public event Action<VideoDoneMessage>? OnVideoDone;
        public event Action<RegisterResultMessage>? OnRegisterResult;
        public event Action? OnScanComplete;
        public event Action<string>? OnError;

        public bool IsConnected => _socketClient.IsConnected;

        public async Task StartAsync(int port = 54321)
        {
            string baseDir = AppDomain.CurrentDomain.BaseDirectory;

            // Resolve python interpreter: bundled first, then fallback to environment
            string[] pythonCandidates = new[]
            {
                Path.Combine(baseDir, "python", "python312", "python.exe"),
                Path.Combine(baseDir, "python", "python.exe"),
                "python.exe"
            };

            string pythonExe = "python.exe";
            foreach (var c in pythonCandidates)
            {
                if (File.Exists(c))
                {
                    pythonExe = c;
                    break;
                }
            }

            // Resolve server.py: bundled engine first, then development BUILD_SOURCES
            string[] serverCandidates = new[]
            {
                Path.Combine(baseDir, "engine", "server.py"),
                Path.GetFullPath(Path.Combine(baseDir, "..", "..", "..", "..", "FaceSeeker.Engine", "BUILD_SOURCES", "server.py")),
                Path.GetFullPath(Path.Combine(baseDir, "..", "..", "..", "FaceSeeker.Engine", "BUILD_SOURCES", "server.py")),
                Path.Combine(Directory.GetCurrentDirectory(), "FaceSeeker.Engine", "BUILD_SOURCES", "server.py")
            };

            string? serverScript = null;
            foreach (var s in serverCandidates)
            {
                if (File.Exists(s))
                {
                    serverScript = s;
                    break;
                }
            }

            if (serverScript == null)
            {
                throw new FileNotFoundException("Could not find server.py in engine/ or BUILD_SOURCES/");
            }

            var psi = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = $"\"{serverScript}\" {port}",
                WorkingDirectory = Path.GetDirectoryName(serverScript)!,
                CreateNoWindow = true,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };

            try
            {
                _process = Process.Start(psi);
                if (_process != null)
                {
                    // FIX: CORRECTNESS-01 — Asynchronously consume stdout and stderr to prevent pipe buffer deadlock
                    _process.OutputDataReceived += (s, e) =>
                    {
                        if (e.Data != null)
                        {
                            Debug.WriteLine($"[Python stdout] {e.Data}");
                        }
                    };
                    _process.ErrorDataReceived += (s, e) =>
                    {
                        if (e.Data != null)
                        {
                            Debug.WriteLine($"[Python stderr] {e.Data}");
                        }
                    };
                    _process.BeginOutputReadLine();
                    _process.BeginErrorReadLine();
                }
            }
            catch (Exception ex)
            {
                throw new InvalidOperationException($"Failed to launch Python server ({pythonExe}): {ex.Message}", ex);
            }

            // Connection retry loop
            bool connected = false;
            for (int i = 0; i < 20; i++)
            {
                await Task.Delay(150);
                if (_process != null && _process.HasExited)
                {
                    throw new InvalidOperationException($"Python process terminated prematurely (exit code: {_process.ExitCode}).");
                }

                try
                {
                    await _socketClient.ConnectAsync("127.0.0.1", port);
                    connected = true;
                    break;
                }
                catch
                {
                    // retry until socket is ready
                }
            }

            if (!connected)
            {
                throw new TimeoutException($"Timed out attempting to connect to Python server on port {port}.");
            }

            // Send ping and wait for pong
            await SendCommandAsync(new SimpleCommand("ping"));
        }

        public async Task ListenAsync(CancellationToken cancellationToken)
        {
            bool scanCompleted = false;
            try
            {
                while (!cancellationToken.IsCancellationRequested && _socketClient.IsConnected)
                {
                    string? line = await _socketClient.ReceiveLineAsync(cancellationToken);
                    if (line == null) break;
                    line = line.Trim();
                    if (string.IsNullOrEmpty(line)) continue;

                    using var doc = JsonDocument.Parse(line);
                    if (doc.RootElement.TryGetProperty("type", out var typeProp))
                    {
                        string? type = typeProp.GetString();
                        switch (type)
                        {
                            case "match":
                                var match = JsonSerializer.Deserialize<MatchMessage>(line);
                                if (match != null) OnMatch?.Invoke(match);
                                break;
                            case "progress":
                                var prog = JsonSerializer.Deserialize<ProgressMessage>(line);
                                if (prog != null) OnProgress?.Invoke(prog);
                                break;
                            case "video_done":
                                var done = JsonSerializer.Deserialize<VideoDoneMessage>(line);
                                if (done != null) OnVideoDone?.Invoke(done);
                                break;
                            case "register_result":
                                var reg = JsonSerializer.Deserialize<RegisterResultMessage>(line);
                                if (reg != null) OnRegisterResult?.Invoke(reg);
                                break;
                            case "scan_complete":
                                scanCompleted = true;
                                OnScanComplete?.Invoke();
                                break;
                            case "error":
                                string msg = doc.RootElement.TryGetProperty("message", out var m) ? m.GetString() ?? "Unknown error" : "Unknown error";
                                OnError?.Invoke(msg);
                                break;
                        }
                    }
                }

                // If socket terminated without cancellation and without scan_complete, connection died
                if (!cancellationToken.IsCancellationRequested && !scanCompleted && !_disposed)
                {
                    OnError?.Invoke("Connection to Python engine was lost unexpectedly.");
                }
            }
            catch (OperationCanceledException)
            {
                // Expected when cancelled
            }
            catch (Exception ex)
            {
                if (!_disposed) OnError?.Invoke($"Bridge communication error: {ex.Message}");
            }
        }

        public async Task SendCommandAsync(object command)
        {
            string json = JsonSerializer.Serialize(command);
            await _socketClient.SendAsync(json);
        }

        public void Dispose()
        {
            if (_disposed) return;
            _disposed = true;

            try
            {
                if (_socketClient.IsConnected)
                {
                    _ = SendCommandAsync(new SimpleCommand("cancel"));
                }
            }
            catch { }

            _socketClient.Dispose();

            if (_process != null && !_process.HasExited)
            {
                try
                {
                    _process.Kill(true);
                    _process.WaitForExit(1000);
                }
                catch { }
                _process.Dispose();
                _process = null;
            }
        }
    }
}