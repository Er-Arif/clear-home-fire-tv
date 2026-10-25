using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using Microsoft.Win32;

namespace ClearHomeSetup {
    internal sealed class ToolAsset {
        public string version { get; set; }
        public string url { get; set; }
        public string sha256 { get; set; }
        public string executable { get; set; }
    }
    internal sealed class ToolConfiguration {
        public ToolAsset python { get; set; }
        public ToolAsset adb { get; set; }
    }
    internal sealed class PreparedTools {
        public string Python;
        public string Adb;
    }
    internal sealed class ToolsManager {
        private readonly string home;
        private readonly ToolConfiguration configuration;
        internal bool ForcePrivate;
        internal ToolsManager(string homeDirectory, string payloadDirectory) {
            home = homeDirectory;
            configuration = new JavaScriptSerializer().Deserialize<ToolConfiguration>(
                File.ReadAllText(Path.Combine(payloadDirectory, "windows", "tools.json")));
        }
        private static IEnumerable<string> Candidates(string file) {
            foreach (string folder in (Environment.GetEnvironmentVariable("PATH") ?? "").Split(Path.PathSeparator)) {
                if (string.IsNullOrWhiteSpace(folder) || folder.IndexOf("WindowsApps", StringComparison.OrdinalIgnoreCase) >= 0) continue;
                string candidate;
                try { candidate = Path.Combine(folder.Trim('"'), file); } catch (ArgumentException) { continue; }
                if (File.Exists(candidate)) yield return candidate;
            }
            if (file == "python.exe") foreach (string path in RegisteredPython()) yield return path;
            if (file == "adb.exe") {
                foreach (string name in new [] { "ANDROID_HOME", "ANDROID_SDK_ROOT" }) {
                    string sdk = Environment.GetEnvironmentVariable(name);
                    if (!string.IsNullOrEmpty(sdk)) yield return Path.Combine(sdk, "platform-tools", file);
                }
                yield return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "Android", "Sdk", "platform-tools", file);
            }
        }
        private static List<string> RegisteredPython() {
            var paths = new List<string>();
            foreach (var hive in new [] { RegistryHive.CurrentUser, RegistryHive.LocalMachine }) {
                foreach (var view in new [] { RegistryView.Registry64, RegistryView.Registry32 }) {
                    try {
                        using (var root = RegistryKey.OpenBaseKey(hive, view))
                        using (var core = root.OpenSubKey(@"SOFTWARE\Python\PythonCore")) {
                            if (core == null) continue;
                            foreach (string version in core.GetSubKeyNames()) {
                                using (var install = core.OpenSubKey(version + @"\InstallPath")) {
                                    if (install == null) continue;
                                    string executable = install.GetValue("ExecutablePath") as string;
                                    string directory = install.GetValue(null) as string;
                                    if (!string.IsNullOrEmpty(executable)) paths.Add(executable);
                                    else if (!string.IsNullOrEmpty(directory)) paths.Add(Path.Combine(directory, "python.exe"));
                                }
                            }
                        }
                    } catch (System.Security.SecurityException) { }
                      catch (UnauthorizedAccessException) { }
                }
            }
            return paths;
        }
        private async Task<bool> Probe(string path, bool python, CancellationToken cancel) {
            if (!File.Exists(path)) return false;
            try {
                var arguments = python ? new [] { "-I", "-c", "import sys;print('CLEAR_HOME_PYTHON_OK');sys.exit(0 if sys.version_info >= (3,11) else 2)" }
                    : new [] { "version" };
                var result = await ProcessRunner.Run(path, arguments, null, cancel, 8);
                return result.ExitCode == 0 && (python ? result.Output.Contains("CLEAR_HOME_PYTHON_OK") : result.Output.Contains("Android Debug Bridge"));
            } catch (OperationCanceledException) { throw; }
            catch (Exception) { return false; }
        }
        private async Task<string> InstallAsset(string label, ToolAsset asset, IProgress<string> progress, CancellationToken cancel) {
            var uri = new Uri(asset.url);
            if (uri.Scheme != "https" || (uri.Host != "www.python.org" && uri.Host != "dl.google.com"))
                throw new InvalidDataException("Unexpected tool download source.");
            string directory = Path.Combine(home, "Tools", label + "-" + asset.version);
            string cache = Path.Combine(home, "Downloads");
            Payload.NoLinks(directory); Payload.NoLinks(cache);
            Directory.CreateDirectory(cache);
            string zip = Path.Combine(cache, label + "-" + asset.version + ".zip");
            if (File.Exists(zip)) {
                try { Payload.Verify(zip, asset.sha256); }
                catch (InvalidDataException) { File.Delete(zip); progress.Report("Discarded an invalid cached " + label + " download."); }
            }
            if (!File.Exists(zip)) {
                progress.Report("Downloading " + label + " " + asset.version + " from " + uri.Host + "...");
                string temporary = zip + "." + Guid.NewGuid().ToString("N") + ".part";
                try {
                    ServicePointManager.SecurityProtocol |= SecurityProtocolType.Tls12;
                    using (var client = new HttpClient()) {
                        client.Timeout = TimeSpan.FromMinutes(5);
                        client.DefaultRequestHeaders.UserAgent.ParseAdd("ClearHome-Windows-Setup/0.3");
                        using (var response = await client.GetAsync(uri, HttpCompletionOption.ResponseHeadersRead, cancel)) {
                            response.EnsureSuccessStatusCode();
                            using (var input = await response.Content.ReadAsStreamAsync())
                            using (var output = new FileStream(temporary, FileMode.CreateNew)) {
                                byte[] buffer = new byte[65536]; long total = 0; int count;
                                while ((count = await input.ReadAsync(buffer, 0, buffer.Length, cancel)) != 0) {
                                    total += count;
                                    if (total > 100L * 1024 * 1024) throw new InvalidDataException("Tool download is too large.");
                                    await output.WriteAsync(buffer, 0, count, cancel);
                                }
                            }
                        }
                    }
                    Payload.Verify(temporary, asset.sha256);
                    File.Move(temporary, zip);
                } finally { if (File.Exists(temporary)) File.Delete(temporary); }
            }
            Payload.Verify(zip, asset.sha256);
            progress.Report("Verified " + label + "; preparing private tools...");
            bool current;
            using (var input = File.OpenRead(zip)) current = Payload.MatchesArchive(input, directory);
            if (!current) using (var input = File.OpenRead(zip)) Payload.Extract(input, directory);
            string executable = Path.Combine(directory, asset.executable.Replace('/', Path.DirectorySeparatorChar));
            if (!await Probe(executable, label == "Python", cancel))
                throw new InvalidDataException(label + " could not start. Windows 10/11 x64 is required.");
            return executable;
        }
        internal async Task<PreparedTools> Prepare(IProgress<string> progress, CancellationToken cancel) {
            if (!Environment.Is64BitOperatingSystem ||
                (Environment.GetEnvironmentVariable("PROCESSOR_ARCHITECTURE") ?? "").Equals("ARM64", StringComparison.OrdinalIgnoreCase))
                throw new NotSupportedException("Automatic setup currently supports Windows 10/11 x64. Use the documented CLI on other systems.");
            var result = new PreparedTools();
            if (!ForcePrivate) {
                foreach (string candidate in Candidates("python.exe")) {
                    if (await Probe(candidate, true, cancel)) { result.Python = candidate; break; }
                }
                foreach (string candidate in Candidates("adb.exe")) {
                    if (await Probe(candidate, false, cancel)) { result.Adb = candidate; break; }
                }
            }
            progress.Report(result.Python == null ? "Preparing Python automatically..." : "Compatible Python found.");
            if (result.Python == null) result.Python = await InstallAsset("Python", configuration.python, progress, cancel);
            progress.Report(result.Adb == null ? "Preparing ADB automatically..." : "ADB found.");
            if (result.Adb == null) result.Adb = await InstallAsset("ADB", configuration.adb, progress, cancel);
            return result;
        }
    }
}
