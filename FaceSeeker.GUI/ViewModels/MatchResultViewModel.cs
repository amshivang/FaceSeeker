// ponytail: clean match result view model with frozen cross-thread BitmapImage
using System;
using System.IO;
using System.Windows.Media.Imaging;
using CommunityToolkit.Mvvm.ComponentModel;
using FaceSeeker.GUI.Models;

namespace FaceSeeker.GUI.ViewModels
{
    public partial class MatchResultViewModel : ObservableObject
    {
        [ObservableProperty]
        private string _targetName = string.Empty;

        [ObservableProperty]
        private string _videoName = string.Empty;

        [ObservableProperty]
        private string _videoPath = string.Empty;

        [ObservableProperty]
        private int _frameNumber;

        [ObservableProperty]
        private string _timestampStr = string.Empty;

        [ObservableProperty]
        private double _confidence;

        [ObservableProperty]
        private string _confidencePct = string.Empty;

        [ObservableProperty]
        private BitmapImage? _thumbnail;

        [ObservableProperty]
        private bool _isHighConf;

        public MatchResultViewModel(MatchMessage m)
        {
            TargetName = m.TargetName;
            VideoPath = m.VideoPath;
            VideoName = string.IsNullOrEmpty(m.VideoPath) ? "Unknown" : Path.GetFileName(m.VideoPath);
            FrameNumber = m.FrameNumber;
            TimestampStr = m.TimestampStr;
            Confidence = m.Confidence;
            ConfidencePct = $"{(m.Confidence * 100):0.0}%";
            IsHighConf = m.Confidence >= 0.75;

            if (!string.IsNullOrEmpty(m.ThumbnailB64))
            {
                try
                {
                    byte[] bytes = Convert.FromBase64String(m.ThumbnailB64);
                    using var stream = new MemoryStream(bytes);
                    var image = new BitmapImage();
                    image.BeginInit();
                    image.CacheOption = BitmapCacheOption.OnLoad;
                    image.StreamSource = stream;
                    image.EndInit();
                    image.Freeze(); // Required for cross-thread access in WPF
                    Thumbnail = image;
                }
                catch
                {
                    Thumbnail = null;
                }
            }
        }
    }
}