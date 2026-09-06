// ponytail: pure data classes for socket serialization, standard library System.Text.Json
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace FaceSeeker.GUI.Models
{
    public class BaseMessage
    {
        [JsonPropertyName("type")]
        public string? Type { get; set; }
    }

    public class MatchMessage : BaseMessage
    {
        [JsonPropertyName("target_name")]
        public string TargetName { get; set; } = string.Empty;

        [JsonPropertyName("video_path")]
        public string VideoPath { get; set; } = string.Empty;

        [JsonPropertyName("frame_number")]
        public int FrameNumber { get; set; }

        [JsonPropertyName("timestamp_str")]
        public string TimestampStr { get; set; } = string.Empty;

        [JsonPropertyName("confidence")]
        public double Confidence { get; set; }

        [JsonPropertyName("thumbnail_b64")]
        public string ThumbnailB64 { get; set; } = string.Empty;

        [JsonPropertyName("bbox")]
        public List<int> Bbox { get; set; } = new();
    }

    public class ProgressMessage : BaseMessage
    {
        [JsonPropertyName("video_path")]
        public string Video { get; set; } = string.Empty;

        [JsonPropertyName("frame_current")]
        public int Current { get; set; }

        [JsonPropertyName("frame_total")]
        public int Total { get; set; }
    }

    public class VideoDoneMessage : BaseMessage
    {
        [JsonPropertyName("video_path")]
        public string VideoPath { get; set; } = string.Empty;

        [JsonPropertyName("total_matches")]
        public int TotalMatches { get; set; }

        [JsonPropertyName("error")]
        public string Error { get; set; } = string.Empty;
    }

    public class RegisterResultMessage : BaseMessage
    {
        [JsonPropertyName("name")]
        public string Name { get; set; } = string.Empty;

        [JsonPropertyName("success")]
        public bool Success { get; set; }

        [JsonPropertyName("error")]
        public string Error { get; set; } = string.Empty;
    }

    public class ScanRequest
    {
        [JsonPropertyName("cmd")]
        public string Cmd { get; set; } = "scan";

        [JsonPropertyName("videos")]
        public List<string> Videos { get; set; } = new();

        [JsonPropertyName("frame_skip")]
        public int FrameSkip { get; set; } = 5;

        [JsonPropertyName("cosine_threshold")]
        public double CosineThreshold { get; set; } = 0.363;
    }

    public class RegisterRequest
    {
        [JsonPropertyName("cmd")]
        public string Cmd { get; set; } = "register_target";

        [JsonPropertyName("name")]
        public string Name { get; set; } = string.Empty;

        [JsonPropertyName("image_b64")]
        public string ImageB64 { get; set; } = string.Empty;
    }

    public class SimpleCommand
    {
        [JsonPropertyName("cmd")]
        public string Cmd { get; set; } = string.Empty;

        public SimpleCommand() { }
        public SimpleCommand(string cmd) => Cmd = cmd;
    }
}