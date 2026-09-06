using System.Collections.Generic;
using FaceSeeker.GUI.Models;
using FaceSeeker.GUI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace FaceSeeker.GUI.Tests
{
    [TestClass]
    public class MatchResultViewModelTests
    {
        // 1x1 transparent PNG encoded in base64
        private const string ValidPngB64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";

        [TestMethod]
        public void Properties_PopulatedCorrectly_FromMatchMessage()
        {
            var msg = new MatchMessage
            {
                TargetName = "Jane Doe",
                VideoPath = @"C:\media\sample_feed.mp4",
                FrameNumber = 240,
                TimestampStr = "00:00:08.000",
                Confidence = 0.825,
                ThumbnailB64 = ""
            };

            var vm = new MatchResultViewModel(msg);

            Assert.AreEqual("Jane Doe", vm.TargetName);
            Assert.AreEqual(@"C:\media\sample_feed.mp4", vm.VideoPath);
            Assert.AreEqual("sample_feed.mp4", vm.VideoName);
            Assert.AreEqual(240, vm.FrameNumber);
            Assert.AreEqual("00:00:08.000", vm.TimestampStr);
            Assert.AreEqual(0.825, vm.Confidence, 0.0001);
            Assert.AreEqual("82.5%", vm.ConfidencePct);
            Assert.IsNull(vm.Thumbnail);
        }

        [TestMethod]
        public void VideoName_DefaultsToUnknown_WhenVideoPathIsEmpty()
        {
            var msg = new MatchMessage
            {
                TargetName = "Jane Doe",
                VideoPath = "",
                FrameNumber = 1,
                TimestampStr = "00:00:00.033",
                Confidence = 0.8
            };

            var vm = new MatchResultViewModel(msg);

            Assert.AreEqual("Unknown", vm.VideoName);
        }

        [TestMethod]
        [DataRow(0.75, true)]
        [DataRow(0.75001, true)]
        [DataRow(0.95, true)]
        [DataRow(0.74999, false)]
        [DataRow(0.74, false)]
        [DataRow(0.363, false)]
        public void IsHighConf_EvaluatesCorrectly(double confidence, bool expectedHighConf)
        {
            var msg = new MatchMessage
            {
                TargetName = "Test",
                VideoPath = "vid.mp4",
                Confidence = confidence
            };

            var vm = new MatchResultViewModel(msg);

            Assert.AreEqual(expectedHighConf, vm.IsHighConf, $"Confidence {confidence} should yield IsHighConf={expectedHighConf}");
        }

        [TestMethod]
        public void Thumbnail_DecodesValidBase64AndFreezes()
        {
            var msg = new MatchMessage
            {
                TargetName = "Target",
                VideoPath = "vid.mp4",
                Confidence = 0.9,
                ThumbnailB64 = ValidPngB64
            };

            var vm = new MatchResultViewModel(msg);

            Assert.IsNotNull(vm.Thumbnail);
            Assert.IsTrue(vm.Thumbnail.IsFrozen);
        }

        [TestMethod]
        public void Thumbnail_HandlesInvalidBase64Gracefully()
        {
            var msg = new MatchMessage
            {
                TargetName = "Target",
                VideoPath = "vid.mp4",
                Confidence = 0.9,
                ThumbnailB64 = "not-a-valid-base64-string!!!"
            };

            var vm = new MatchResultViewModel(msg);

            Assert.IsNull(vm.Thumbnail);
        }
    }
}
