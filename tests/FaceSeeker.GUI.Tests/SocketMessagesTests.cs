using System.Collections.Generic;
using System.Text.Json;
using FaceSeeker.GUI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace FaceSeeker.GUI.Tests
{
    [TestClass]
    public class SocketMessagesTests
    {
        [TestMethod]
        public void ScanRequest_SerializesCosineThresholdAndExpectedFields()
        {
            var req = new ScanRequest
            {
                Cmd = "scan",
                Videos = new List<string> { @"C:\videos\clip1.mp4", @"C:\videos\clip2.mp4" },
                FrameSkip = 10,
                CosineThreshold = 0.425
            };

            string json = JsonSerializer.Serialize(req);
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            Assert.AreEqual("scan", root.GetProperty("cmd").GetString());
            Assert.AreEqual(10, root.GetProperty("frame_skip").GetInt32());
            Assert.AreEqual(0.425, root.GetProperty("cosine_threshold").GetDouble(), 0.0001);

            var videos = root.GetProperty("videos");
            Assert.AreEqual(2, videos.GetArrayLength());
            Assert.AreEqual(@"C:\videos\clip1.mp4", videos[0].GetString());
            Assert.AreEqual(@"C:\videos\clip2.mp4", videos[1].GetString());
        }

        [TestMethod]
        public void RegisterRequest_SerializesExpectedFields()
        {
            var req = new RegisterRequest
            {
                Cmd = "register_target",
                Name = "John Doe",
                ImageB64 = "base64encodedimagecontent"
            };

            string json = JsonSerializer.Serialize(req);
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            Assert.AreEqual("register_target", root.GetProperty("cmd").GetString());
            Assert.AreEqual("John Doe", root.GetProperty("name").GetString());
            Assert.AreEqual("base64encodedimagecontent", root.GetProperty("image_b64").GetString());
        }

        [TestMethod]
        public void RegisterResultMessage_DeserializesCorrectly()
        {
            string json = """
            {
                "type": "register_result",
                "name": "Jane Doe",
                "success": true,
                "error": ""
            }
            """;

            var msg = JsonSerializer.Deserialize<RegisterResultMessage>(json);

            Assert.IsNotNull(msg);
            Assert.AreEqual("register_result", msg.Type);
            Assert.AreEqual("Jane Doe", msg.Name);
            Assert.IsTrue(msg.Success);
            Assert.AreEqual("", msg.Error);
        }

        [TestMethod]
        public void MatchMessage_DeserializesCorrectly()
        {
            string json = """
            {
                "type": "match",
                "target_name": "Alice",
                "video_path": "C:\\videos\\test.mp4",
                "frame_number": 150,
                "timestamp_str": "00:00:05.000",
                "confidence": 0.892,
                "thumbnail_b64": "abc123",
                "bbox": [10, 20, 100, 120]
            }
            """;

            var msg = JsonSerializer.Deserialize<MatchMessage>(json);

            Assert.IsNotNull(msg);
            Assert.AreEqual("match", msg.Type);
            Assert.AreEqual("Alice", msg.TargetName);
            Assert.AreEqual("C:\\videos\\test.mp4", msg.VideoPath);
            Assert.AreEqual(150, msg.FrameNumber);
            Assert.AreEqual("00:00:05.000", msg.TimestampStr);
            Assert.AreEqual(0.892, msg.Confidence, 0.0001);
            Assert.AreEqual("abc123", msg.ThumbnailB64);
            CollectionAssert.AreEqual(new List<int> { 10, 20, 100, 120 }, msg.Bbox);
        }

        [TestMethod]
        public void VideoDoneMessage_DeserializesCorrectly()
        {
            string json = """
            {
                "type": "video_done",
                "video_path": "C:\\videos\\sample.mp4",
                "total_matches": 12,
                "error": ""
            }
            """;

            var msg = JsonSerializer.Deserialize<VideoDoneMessage>(json);

            Assert.IsNotNull(msg);
            Assert.AreEqual("video_done", msg.Type);
            Assert.AreEqual("C:\\videos\\sample.mp4", msg.VideoPath);
            Assert.AreEqual(12, msg.TotalMatches);
            Assert.AreEqual("", msg.Error);
        }

        [TestMethod]
        public void ProgressMessage_DeserializesCorrectly()
        {
            string json = """
            {
                "type": "progress",
                "video_path": "sample.mp4",
                "frame_current": 50,
                "frame_total": 200
            }
            """;

            var msg = JsonSerializer.Deserialize<ProgressMessage>(json);

            Assert.IsNotNull(msg);
            Assert.AreEqual("progress", msg.Type);
            Assert.AreEqual("sample.mp4", msg.Video);
            Assert.AreEqual(50, msg.Current);
            Assert.AreEqual(200, msg.Total);
        }

        [TestMethod]
        public void SimpleCommand_SerializesCorrectly()
        {
            var cmd = new SimpleCommand("stop");
            string json = JsonSerializer.Serialize(cmd);
            using var doc = JsonDocument.Parse(json);

            Assert.AreEqual("stop", doc.RootElement.GetProperty("cmd").GetString());
        }
    }
}
