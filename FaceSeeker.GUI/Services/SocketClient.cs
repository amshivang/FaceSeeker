// ponytail: clean low-level socket client using standard TcpClient and UTF-8 streams
using System;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;

namespace FaceSeeker.GUI.Services
{
    public class SocketClient : IDisposable
    {
        private TcpClient? _client;
        private NetworkStream? _stream;
        private StreamReader? _reader;
        private StreamWriter? _writer;
        private readonly object _lock = new();

        public bool IsConnected => _client != null && _client.Connected;

        public async Task ConnectAsync(string host, int port)
        {
            Dispose();
            _client = new TcpClient();
            await _client.ConnectAsync(host, port);
            _stream = _client.GetStream();
            _reader = new StreamReader(_stream, Encoding.UTF8);
            _writer = new StreamWriter(_stream, Encoding.UTF8) { AutoFlush = true };
        }

        public async Task SendAsync(string json)
        {
            if (_writer == null) throw new InvalidOperationException("Socket is not connected.");
            await _writer.WriteLineAsync(json);
        }

        public async Task<string?> ReceiveLineAsync(System.Threading.CancellationToken cancellationToken = default)
        {
            if (_reader == null) return null;
            try
            {
                return await _reader.ReadLineAsync(cancellationToken);
            }
            catch (OperationCanceledException)
            {
                return null;
            }
            catch
            {
                return null;
            }
        }

        public void Dispose()
        {
            lock (_lock)
            {
                try { _writer?.Dispose(); } catch { }
                try { _reader?.Dispose(); } catch { }
                try { _stream?.Dispose(); } catch { }
                try { _client?.Dispose(); } catch { }
                _writer = null;
                _reader = null;
                _stream = null;
                _client = null;
            }
        }
    }
}