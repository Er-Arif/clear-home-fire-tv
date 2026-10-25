using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Text;
using System.Threading;

namespace ClearHomeSetup {
    internal static class SelfTests {
        internal static int Run(string reportPath) {
            var report = new List<string>();
            string baseTemp = Path.GetFullPath(Path.GetTempPath());
            string root = Path.Combine(baseTemp, "clear-home-tests-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(root);
            Action<bool, string> check = (condition, message) => {
                if (!condition) throw new Exception("FAILED: " + message);
                report.Add("PASS: " + message);
            };
            try {
                var endpoints = MainForm.ParseDevices("adb-one _adb._tcp 192.168.1.20:5555\n"
                    + "adb-one _adb-tls-connect._tcp 192.168.1.20:41234\n"
                    + "adb-two _adb-tls-pairing._tcp 192.168.1.21:49000", "192.168.1.20:5555 device\n");
                check(endpoints.Count == 1 && endpoints[0] == "192.168.1.20:5555", "Discovery deduplicates endpoints and excludes pairing advertisements");
                check(ProcessRunner.Quote("a b") == "\"a b\"", "Quote arguments with spaces");
                check(ProcessRunner.Quote("C:\\end\\") == "\"C:\\end\\\\\"", "Quote trailing backslash");
                check(ProcessRunner.Quote("a\"b") == "\"a\\\"b\"", "Quote embedded double quote");
                string hashFile = Path.Combine(root, "hash.txt"); File.WriteAllText(hashFile, "hello", new UTF8Encoding(false));
                Payload.Verify(hashFile, "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824");
                check(true, "Accept matching SHA-256");
                bool rejected = false;
                try { Payload.Verify(hashFile, new string('0', 64)); } catch (InvalidDataException) { rejected = true; }
                check(rejected, "Reject checksum mismatch");
                using (var memory = MakeZip("nested/file.txt")) {
                    Payload.Extract(memory, Path.Combine(root, "safe"));
                    check(File.ReadAllText(Path.Combine(root, "safe/nested/file.txt")) == "ok", "Extract normal archive within destination");
                    memory.Position = 0;
                    check(Payload.MatchesArchive(memory, Path.Combine(root, "safe")), "Reuse a matching tool cache without overwriting running binaries");
                    File.WriteAllText(Path.Combine(root, "safe/nested/file.txt"), "changed"); memory.Position = 0;
                    check(!Payload.MatchesArchive(memory, Path.Combine(root, "safe")), "Detect a changed tool cache");
                }
                foreach (string unsafeName in new [] { "../outside.txt", "..\\outside.txt", "C:/absolute.txt", "/absolute.txt" }) {
                    rejected = false;
                    try { using (var memory = MakeZip(unsafeName)) Payload.Extract(memory, Path.Combine(root, "unsafe")); }
                    catch (InvalidDataException) { rejected = true; }
                    check(rejected, "Reject unsafe archive path: " + unsafeName);
                }
                using (var embedded = Assembly.GetExecutingAssembly().GetManifestResourceStream("ClearHome.Payload")) {
                    check(embedded != null && embedded.Length > 0, "Embedded setup payload present");
                }
                string exe = Assembly.GetExecutingAssembly().Location;
                var echo = ProcessRunner.Run(exe, new [] { "--test-echo", "a b\"c\\" }, null, CancellationToken.None, 10).GetAwaiter().GetResult();
                check(echo.ExitCode == 0 && echo.Output.Trim() == Convert.ToBase64String(Encoding.UTF8.GetBytes("a b\"c\\")), "Native argument round trip");
                bool timedOut = false;
                try { ProcessRunner.Run(exe, new [] { "--test-sleep" }, null, CancellationToken.None, 1).GetAwaiter().GetResult(); }
                catch (TimeoutException) { timedOut = true; }
                check(timedOut, "Child timeout is bounded");
                using (var canceled = new CancellationTokenSource()) {
                    canceled.Cancel(); rejected = false;
                    try { ProcessRunner.Run(exe, new [] { "--test-sleep" }, null, canceled.Token, 10).GetAwaiter().GetResult(); }
                    catch (OperationCanceledException) { rejected = true; }
                    check(rejected, "Canceled work does not start a child");
                }
                File.WriteAllLines(reportPath, report); return 0;
            } catch (Exception error) {
                report.Add(error.ToString()); File.WriteAllLines(reportPath, report); return 1;
            } finally {
                string resolved = Path.GetFullPath(root);
                if (resolved.StartsWith(baseTemp.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)
                    && Path.GetFileName(resolved).StartsWith("clear-home-tests-", StringComparison.Ordinal)) Directory.Delete(resolved, true);
            }
        }
        private static MemoryStream MakeZip(string path) {
            var memory = new MemoryStream();
            using (var archive = new ZipArchive(memory, ZipArchiveMode.Create, true)) {
                using (var writer = new StreamWriter(archive.CreateEntry(path).Open())) writer.Write("ok");
            }
            memory.Position = 0; return memory;
        }
    }
}
