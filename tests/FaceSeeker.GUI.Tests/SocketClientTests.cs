using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;
using FaceSeeker.GUI.Services;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace FaceSeeker.GUI.Tests
{
    [TestClass]
    public class SocketClientTests
    {
        [TestMethod]
        public async Task SocketClient_ConcurrentSendAsync_DoesNotCorruptOrThrow()
        {
            var listener = new TcpListener(IPAddress.Loopback, 0);
            listener.Start();
            int port = ((IPEndPoint)listener.LocalEndpoint).Port;

            var receivedLines = new List<string>();
            var serverTask = Task.Run(async () =>
            {
                using var serverConn = await listener.AcceptTcpClientAsync();
                using var stream = serverConn.GetStream();
                using var reader = new StreamReader(stream, Encoding.UTF8);

                while (true)
                {
                    string? line = await reader.ReadLineAsync();
                    if (line == null) break;
                    lock (receivedLines)
                    {
                        receivedLines.Add(line);
                    }
                    if (receivedLines.Count >= 50) break;
                }
            });

            using var client = new SocketClient();
            await client.ConnectAsync("127.0.0.1", port);
            Assert.IsTrue(client.IsConnected);

            var sendTasks = new List<Task>();
            for (int i = 0; i < 50; i++)
            {
                int index = i;
                sendTasks.Add(Task.Run(async () =>
                {
                    await client.SendAsync($"{{\"msg_index\": {index}}}");
                }));
            }

            await Task.WhenAll(sendTasks);
            await Task.WhenAny(serverTask, Task.Delay(2000));

            listener.Stop();

            lock (receivedLines)
            {
                Assert.AreEqual(50, receivedLines.Count, "All 50 concurrent messages should arrive without corruption or truncation.");
                foreach (var line in receivedLines)
                {
                    Assert.IsTrue(line.StartsWith("{\"msg_index\":") && line.EndsWith("}"), $"Line was corrupted: {line}");
                }
            }
        }
    }
}
