// ponytail: clean export service, pure file writing using stdlib IO and Text.Json
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using FaceSeeker.GUI.ViewModels;

namespace FaceSeeker.GUI.Services
{
    public class ExportService
    {
        public void ExportCsv(IEnumerable<MatchResultViewModel> results, string filePath)
        {
            var sb = new StringBuilder();
            sb.AppendLine("Name,Video,Timestamp,Confidence,Frame");

            foreach (var r in results)
            {
                string safeName = EscapeCsv(r.TargetName);
                string safeVideo = EscapeCsv(r.VideoName);
                sb.AppendLine($"{safeName},{safeVideo},{r.TimestampStr},{r.Confidence.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture)},{r.FrameNumber}");
            }

            File.WriteAllText(filePath, sb.ToString(), Encoding.UTF8);
        }

        public void ExportJson(IEnumerable<MatchResultViewModel> results, string filePath)
        {
            var data = results.Select(r => new
            {
                name = r.TargetName,
                video = r.VideoName,
                video_path = r.VideoPath,
                timestamp = r.TimestampStr,
                confidence = r.Confidence,
                confidence_pct = r.ConfidencePct,
                frame = r.FrameNumber
            });

            string json = JsonSerializer.Serialize(data, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(filePath, json, Encoding.UTF8);
        }

        public void ExportTxtReport(IEnumerable<MatchResultViewModel> results, string filePath)
        {
            var sb = new StringBuilder();
            sb.AppendLine("==================================================");
            sb.AppendLine("              FACE SEEKER MATCH REPORT            ");
            sb.AppendLine($" Generated: {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
            sb.AppendLine($" Total Matches: {results.Count()}");
            sb.AppendLine("==================================================");
            sb.AppendLine();

            var byTarget = results.GroupBy(r => r.TargetName);
            foreach (var targetGroup in byTarget)
            {
                sb.AppendLine($"Target: {targetGroup.Key}");
                sb.AppendLine("--------------------------------------------------");

                var byVideo = targetGroup.GroupBy(r => r.VideoName);
                foreach (var videoGroup in byVideo)
                {
                    sb.AppendLine($"  {targetGroup.Key} found {videoGroup.Count()} time(s) in {videoGroup.Key}:");
                    foreach (var match in videoGroup.OrderBy(m => m.FrameNumber))
                    {
                        sb.AppendLine($"    -> {match.TimestampStr} ({match.ConfidencePct}) [Frame {match.FrameNumber}]");
                    }
                    sb.AppendLine();
                }
            }

            File.WriteAllText(filePath, sb.ToString(), Encoding.UTF8);
        }

        private static string EscapeCsv(string val)
        {
            if (string.IsNullOrEmpty(val)) return "";
            if (val.Contains(',') || val.Contains('"') || val.Contains('\n') || val.Contains('\r'))
            {
                return $"\"{val.Replace("\"", "\"\"")}\"";
            }
            return val;
        }
    }
}