// ponytail: clean configuration model using standard library System.Text.Json
using System;
using System.IO;
using System.Text.Json;

namespace FaceSeeker.GUI.Models
{
    public class AppSettings
    {
        public int FrameSkip { get; set; } = 5;
        public double CosineThreshold { get; set; } = 0.363;
        public int ServerPort { get; set; } = 54321;
        public string LastVideoFolder { get; set; } = string.Empty;
        public string LastExportFolder { get; set; } = string.Empty;
        public int DuplicateSuppressSeconds { get; set; } = 3;

        private static string GetSettingsPath()
        {
            string appData = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "FaceSeeker"
            );
            if (!Directory.Exists(appData))
            {
                Directory.CreateDirectory(appData);
            }
            return Path.Combine(appData, "settings.json");
        }

        public static AppSettings Load()
        {
            try
            {
                string path = GetSettingsPath();
                if (File.Exists(path))
                {
                    string json = File.ReadAllText(path);
                    var settings = JsonSerializer.Deserialize<AppSettings>(json);
                    if (settings != null) return settings;
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[AppSettings] Failed to load settings: {ex.Message}");
            }
            return new AppSettings();
        }

        public void Save()
        {
            try
            {
                string path = GetSettingsPath();
                string json = JsonSerializer.Serialize(this, new JsonSerializerOptions { WriteIndented = true });
                File.WriteAllText(path, json);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[AppSettings] Failed to save settings: {ex.Message}");
            }
        }
    }
}