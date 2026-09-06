using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text.Json;
using System.Threading;
using FaceSeeker.GUI.Models;
using FaceSeeker.GUI.Services;
using FaceSeeker.GUI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace FaceSeeker.GUI.Tests
{
    [TestClass]
    public class ExportServiceTests
    {
        private string _tempDir = null!;
        private ExportService _service = null!;

        [TestInitialize]
        public void Setup()
        {
            _tempDir = Path.Combine(Path.GetTempPath(), "FaceSeekerTests_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_tempDir);
            _service = new ExportService();
        }

        [TestCleanup]
        public void Cleanup()
        {
            if (Directory.Exists(_tempDir))
            {
                try
                {
                    Directory.Delete(_tempDir, true);
                }
                catch
                {
                    // Ignore transient cleanup errors
                }
            }
        }

        private static MatchResultViewModel CreateMatch(
            string targetName = "Target A",
            string videoPath = @"C:\videos\sample.mp4",
            int frame = 120,
            string timestamp = "00:00:04.000",
            double confidence = 0.8523)
        {
            var msg = new MatchMessage
            {
                TargetName = targetName,
                VideoPath = videoPath,
                FrameNumber = frame,
                TimestampStr = timestamp,
                Confidence = confidence
            };
            return new MatchResultViewModel(msg);
        }

        [TestMethod]
        public void ExportCsv_WritesHeaderAndExpectedColumns()
        {
            string csvPath = Path.Combine(_tempDir, "test.csv");
            var matches = new List<MatchResultViewModel>
            {
                CreateMatch("Alice", @"C:\vids\camera1.mp4", 100, "00:00:03.333", 0.912)
            };

            _service.ExportCsv(matches, csvPath);

            Assert.IsTrue(File.Exists(csvPath));
            string[] lines = File.ReadAllLines(csvPath);
            Assert.IsTrue(lines.Length >= 2);
            Assert.AreEqual("Name,Video,Timestamp,Confidence,Frame", lines[0]);
            Assert.AreEqual("Alice,camera1.mp4,00:00:03.333,0.912,100", lines[1]);
        }

        [TestMethod]
        public void ExportCsv_EscapesCommasQuotesAndCarriageReturns()
        {
            string csvPath = Path.Combine(_tempDir, "escaped.csv");
            var matches = new List<MatchResultViewModel>
            {
                CreateMatch(
                    targetName: "Doe, John \"The Boss\"",
                    videoPath: "C:\\vids\\clip\r\nwith,comma.mp4",
                    frame: 50,
                    timestamp: "00:00:01.000",
                    confidence: 0.777)
            };

            _service.ExportCsv(matches, csvPath);

            string content = File.ReadAllText(csvPath);
            // Comma and quotes in target name should be quoted with doubled quotes
            Assert.IsTrue(content.Contains("\"Doe, John \"\"The Boss\"\"\""), "Quotes and commas should be properly escaped.");
            // Video name contains comma and newline, so it should also be quoted
            Assert.IsTrue(content.Contains("\"clip\r\nwith,comma.mp4\""), "Video name with comma/CRLF should be quoted.");
        }

        [TestMethod]
        public void ExportCsv_UsesInvariantDecimalSeparatorRegardlessOfCulture()
        {
            var originalCulture = Thread.CurrentThread.CurrentCulture;
            try
            {
                // Culture where comma is decimal separator
                Thread.CurrentThread.CurrentCulture = new CultureInfo("de-DE");

                string csvPath = Path.Combine(_tempDir, "culture.csv");
                var matches = new List<MatchResultViewModel>
                {
                    CreateMatch(confidence: 0.850)
                };

                _service.ExportCsv(matches, csvPath);

                string content = File.ReadAllText(csvPath);
                Assert.IsTrue(content.Contains(",0.850,"), $"Expected invariant decimal dot '0.850', but got: {content}");
                Assert.IsFalse(content.Contains(",0,850,"), "Decimal comma should not appear in confidence column.");
            }
            finally
            {
                Thread.CurrentThread.CurrentCulture = originalCulture;
            }
        }

        [TestMethod]
        public void ExportJson_ProducesValidJsonWithExpectedProperties()
        {
            string jsonPath = Path.Combine(_tempDir, "export.json");
            var matches = new List<MatchResultViewModel>
            {
                CreateMatch("Bob", @"D:\movies\film.mp4", 450, "00:00:15.000", 0.8845)
            };

            _service.ExportJson(matches, jsonPath);

            Assert.IsTrue(File.Exists(jsonPath));
            string json = File.ReadAllText(jsonPath);

            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;
            Assert.AreEqual(JsonValueKind.Array, root.ValueKind);
            Assert.AreEqual(1, root.GetArrayLength());

            var item = root[0];
            Assert.AreEqual("Bob", item.GetProperty("name").GetString());
            Assert.AreEqual("film.mp4", item.GetProperty("video").GetString());
            Assert.AreEqual(@"D:\movies\film.mp4", item.GetProperty("video_path").GetString());
            Assert.AreEqual("00:00:15.000", item.GetProperty("timestamp").GetString());
            Assert.AreEqual(0.8845, item.GetProperty("confidence").GetDouble(), 0.0001);
            Assert.AreEqual("88.5%", item.GetProperty("confidence_pct").GetString());
            Assert.AreEqual(450, item.GetProperty("frame").GetInt32());
        }

        [TestMethod]
        public void ExportTxtReport_CreatesReadableGroupedOutput()
        {
            string txtPath = Path.Combine(_tempDir, "report.txt");
            var matches = new List<MatchResultViewModel>
            {
                CreateMatch("Target1", @"C:\vids\vidA.mp4", 10, "00:00:00.333", 0.95),
                CreateMatch("Target1", @"C:\vids\vidA.mp4", 50, "00:00:01.667", 0.91),
                CreateMatch("Target1", @"C:\vids\vidB.mp4", 30, "00:00:01.000", 0.80),
                CreateMatch("Target2", @"C:\vids\vidB.mp4", 100, "00:00:03.333", 0.88)
            };

            _service.ExportTxtReport(matches, txtPath);

            Assert.IsTrue(File.Exists(txtPath));
            string text = File.ReadAllText(txtPath);

            StringAssert.Contains(text, "FACE SEEKER MATCH REPORT");
            StringAssert.Contains(text, "Total Matches: 4");
            StringAssert.Contains(text, "Target: Target1");
            StringAssert.Contains(text, "Target1 found 2 time(s) in vidA.mp4:");
            StringAssert.Contains(text, "Target1 found 1 time(s) in vidB.mp4:");
            StringAssert.Contains(text, "Target: Target2");
            StringAssert.Contains(text, "Target2 found 1 time(s) in vidB.mp4:");
            StringAssert.Contains(text, "-> 00:00:00.333 (95.0%) [Frame 10]");
        }
    }
}
