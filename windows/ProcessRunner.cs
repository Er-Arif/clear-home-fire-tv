using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace ClearHomeSetup {
    internal sealed class CommandResult {
        public int ExitCode;
        public string Output;
    }

    internal static class ProcessRunner {
        internal static string Quote(string value) {
            if (value.IndexOf('\0') >= 0) throw new ArgumentException("Invalid command argument.");
            var result = new StringBuilder("\"");
            int slashes = 0;
            foreach (char character in value) {
                if (character == '\\') { slashes++; continue; }
                if (character == '"') {
                    result.Append('\\', slashes * 2 + 1).Append('"');
                } else {
                    result.Append('\\', slashes).Append(character);
                }
                slashes = 0;
            }
            return result.Append('\\', slashes * 2).Append('"').ToString();
        }

        internal static Task<CommandResult> Run(string executable, IEnumerable<string> arguments,
                IProgress<string> progress, CancellationToken cancellation, int timeoutSeconds) {
            return Task.Run(() => {
                var encoded = new List<string>();
                foreach (string argument in arguments) encoded.Add(Quote(argument));
                var info = new ProcessStartInfo(executable, string.Join(" ", encoded));
                info.UseShellExecute = false;
                info.CreateNoWindow = true;
                info.RedirectStandardOutput = true;
                info.RedirectStandardError = true;
                info.StandardOutputEncoding = Encoding.UTF8;
                info.StandardErrorEncoding = Encoding.UTF8;
                info.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
                info.EnvironmentVariables["PYTHONUNBUFFERED"] = "1";
                var output = new StringBuilder();
                object gate = new object();
                using (var process = new Process()) {
                    process.StartInfo = info;
                    DataReceivedEventHandler receive = (sender, item) => {
                        if (item.Data == null) return;
                        lock (gate) { output.AppendLine(item.Data); }
                        if (progress != null) progress.Report(item.Data);
                    };
                    process.OutputDataReceived += receive;
                    process.ErrorDataReceived += receive;
                    process.Start();
                    process.BeginOutputReadLine();
                    process.BeginErrorReadLine();
                    var timer = Stopwatch.StartNew();
                    while (!process.WaitForExit(100)) {
                        if (cancellation.IsCancellationRequested || timer.Elapsed.TotalSeconds > timeoutSeconds) {
                            try { process.Kill(); } catch (InvalidOperationException) { }
                            if (cancellation.IsCancellationRequested) throw new OperationCanceledException(cancellation);
                            throw new TimeoutException("This step timed out. Check the network and try again.");
                        }
                    }
                    process.WaitForExit();
                    return new CommandResult { ExitCode = process.ExitCode, Output = output.ToString() };
                }
            }, cancellation);
        }
    }
}
