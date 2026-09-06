// ponytail: clean target face item model
using System;
using System.IO;
using System.Windows.Media.Imaging;

namespace FaceSeeker.GUI.Models
{
    public class TargetFaceItem
    {
        public string PersonName { get; set; } = string.Empty;
        public string ImagePath { get; set; } = string.Empty;
        public string ImageB64 { get; set; } = string.Empty;
        public BitmapImage? Thumbnail { get; set; }

        public static TargetFaceItem FromFile(string name, string imagePath)
        {
            using var stream = new FileStream(imagePath, FileMode.Open, FileAccess.Read, FileShare.Read);
            var decoder = BitmapDecoder.Create(stream, BitmapCreateOptions.DelayCreation, BitmapCacheOption.None);
            int origW = decoder.Frames[0].PixelWidth;
            int origH = decoder.Frames[0].PixelHeight;

            stream.Position = 0;
            var bmp = new BitmapImage();
            bmp.BeginInit();
            bmp.CacheOption = BitmapCacheOption.OnLoad;
            if (origW >= origH && origW > 1000)
            {
                bmp.DecodePixelWidth = 1000;
            }
            else if (origH > origW && origH > 1000)
            {
                bmp.DecodePixelHeight = 1000;
            }
            bmp.StreamSource = stream;
            bmp.EndInit();
            bmp.Freeze();

            var encoder = new JpegBitmapEncoder { QualityLevel = 90 };
            encoder.Frames.Add(BitmapFrame.Create(bmp));
            using var ms = new MemoryStream();
            encoder.Save(ms);
            byte[] scaledBytes = ms.ToArray();
            string b64 = Convert.ToBase64String(scaledBytes);

            return new TargetFaceItem
            {
                PersonName = name,
                ImagePath = imagePath,
                ImageB64 = b64,
                Thumbnail = bmp
            };
        }
    }
}