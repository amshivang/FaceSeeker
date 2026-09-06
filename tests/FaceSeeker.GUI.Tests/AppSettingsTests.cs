using System.Text.Json;
using FaceSeeker.GUI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace FaceSeeker.GUI.Tests
{
    [TestClass]
    public class AppSettingsTests
    {
        [TestMethod]
        public void DefaultValues_AreCorrect()
        {
            var settings = new AppSettings();

            Assert.AreEqual(5, settings.FrameSkip);
            Assert.AreEqual(0.363, settings.CosineThreshold, 0.0001);
            Assert.AreEqual(54321, settings.ServerPort);
            Assert.AreEqual(string.Empty, settings.LastVideoFolder);
            Assert.AreEqual(string.Empty, settings.LastExportFolder);
            Assert.AreEqual(3, settings.DuplicateSuppressSeconds);
        }

        [TestMethod]
        public void SerializationRoundtrip_PreservesAllProperties()
        {
            var original = new AppSettings
            {
                FrameSkip = 10,
                CosineThreshold = 0.450,
                ServerPort = 12345,
                LastVideoFolder = @"C:\Users\Test\Videos",
                LastExportFolder = @"C:\Users\Test\Exports",
                DuplicateSuppressSeconds = 7
            };

            string json = JsonSerializer.Serialize(original);
            var deserialized = JsonSerializer.Deserialize<AppSettings>(json);

            Assert.IsNotNull(deserialized);
            Assert.AreEqual(original.FrameSkip, deserialized.FrameSkip);
            Assert.AreEqual(original.CosineThreshold, deserialized.CosineThreshold, 0.0001);
            Assert.AreEqual(original.ServerPort, deserialized.ServerPort);
            Assert.AreEqual(original.LastVideoFolder, deserialized.LastVideoFolder);
            Assert.AreEqual(original.LastExportFolder, deserialized.LastExportFolder);
            Assert.AreEqual(original.DuplicateSuppressSeconds, deserialized.DuplicateSuppressSeconds);
        }
    }
}
