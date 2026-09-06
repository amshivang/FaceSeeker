// ponytail: clean settings window with validation and persistence
using System;
using System.IO;
using System.Windows;
using FaceSeeker.GUI.Models;
using Microsoft.Win32;

namespace FaceSeeker.GUI.Views
{
    public partial class SettingsWindow : Window
    {
        private readonly AppSettings _settings;

        public SettingsWindow(AppSettings settings)
        {
            InitializeComponent();
            _settings = settings;
            LoadValues();
        }

        private void LoadValues()
        {
            FrameSkipSlider.Value = _settings.FrameSkip;
            CosineSlider.Value = _settings.CosineThreshold;
            DedupeSlider.Value = _settings.DuplicateSuppressSeconds;
            PortBox.Text = _settings.ServerPort.ToString();
            ExportFolderBox.Text = _settings.LastExportFolder;

            UpdateDisplays();
        }

        private void UpdateDisplays()
        {
            FrameSkipDisplay.Text = ((int)FrameSkipSlider.Value).ToString();
            CosineDisplay.Text = CosineSlider.Value.ToString("0.000");
            DedupeDisplay.Text = $"{((int)DedupeSlider.Value)}s";
        }

        private void OnFrameSkipChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (FrameSkipDisplay != null) FrameSkipDisplay.Text = ((int)e.NewValue).ToString();
        }

        private void OnCosineChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (CosineDisplay != null) CosineDisplay.Text = e.NewValue.ToString("0.000");
        }

        private void OnDedupeChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (DedupeDisplay != null) DedupeDisplay.Text = $"{((int)e.NewValue)}s";
        }

        private void OnBrowseExportFolderClick(object sender, RoutedEventArgs e)
        {
            var dlg = new OpenFolderDialog
            {
                Title = "Select Default Export Folder"
            };
            if (Directory.Exists(ExportFolderBox.Text))
            {
                dlg.InitialDirectory = ExportFolderBox.Text;
            }
            if (dlg.ShowDialog() == true)
            {
                ExportFolderBox.Text = dlg.FolderName;
            }
        }

        private void OnResetDefaultsClick(object sender, RoutedEventArgs e)
        {
            var def = new AppSettings();
            FrameSkipSlider.Value = def.FrameSkip;
            CosineSlider.Value = def.CosineThreshold;
            DedupeSlider.Value = def.DuplicateSuppressSeconds;
            PortBox.Text = def.ServerPort.ToString();
            UpdateDisplays();
        }

        private void OnSaveClick(object sender, RoutedEventArgs e)
        {
            if (!int.TryParse(PortBox.Text.Trim(), out int port) || port < 1024 || port > 65535)
            {
                MessageBox.Show("Please enter a valid TCP port number between 1024 and 65535.", "Validation Error", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            _settings.FrameSkip = (int)FrameSkipSlider.Value;
            _settings.CosineThreshold = Math.Round(CosineSlider.Value, 4);
            _settings.DuplicateSuppressSeconds = (int)DedupeSlider.Value;
            _settings.ServerPort = port;
            _settings.LastExportFolder = ExportFolderBox.Text.Trim();

            _settings.Save();
            DialogResult = true;
            Close();
        }

        private void OnCancelClick(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }
    }
}