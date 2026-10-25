using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace ClearHomeSetup {
    internal sealed class MainForm : Form {
        private readonly string home;
        private readonly string payload;
        private readonly bool preview;
        private PreparedTools tools;
        private CancellationTokenSource cancellation;
        private readonly ComboBox address = new ComboBox();
        private readonly Button find = new Button();
        private readonly Button install = new Button();
        private readonly Button undo = new Button();
        private readonly Button cancel = new Button();
        private readonly CheckBox faster = new CheckBox();
        private readonly TextBox log = new TextBox();
        private readonly Label status = new Label();
        private readonly ProgressBar progress = new ProgressBar();

        internal MainForm(string homeDirectory, string payloadDirectory, bool previewMode) {
            home = homeDirectory; payload = payloadDirectory; preview = previewMode;
            Text = "Clear Home for Fire TV - Setup";
            AutoScaleMode = AutoScaleMode.Dpi; AutoScaleDimensions = new SizeF(96F, 96F);
            ClientSize = new Size(820, 650); MinimumSize = new Size(836, 689);
            StartPosition = FormStartPosition.CenterScreen;
            Font = new Font("Segoe UI", 10); BackColor = Color.FromArgb(245, 247, 251);
            var title = new Label { Text = "A calmer home for your Fire TV", Font = new Font("Segoe UI", 22, FontStyle.Bold),
                Location = new Point(28, 22), Size = new Size(760, 48) };
            Controls.Add(title);
            Controls.Add(new Label { Text = "Python and ADB are checked and prepared automatically. No administrator access needed.",
                Location = new Point(30, 77), Size = new Size(760, 30) });
            var instructions = new Label { Location = new Point(30, 115), Size = new Size(760, 70),
                Text = "On your TV, enable ADB Debugging in Developer Options. Keep the TV and PC on the same Wi-Fi.\r\n"
                    + "Approve the debugging prompt when it appears. At the end, choose Clear Home in Home on Fire." };
            Controls.Add(instructions);
            Controls.Add(new Label { Text = "TV address (IP:port)", Location = new Point(30, 193), Size = new Size(350, 25) });
            address.Location = new Point(30, 221); address.Size = new Size(475, 30); address.DropDownStyle = ComboBoxStyle.DropDown;
            Controls.Add(address);
            find.Text = "Find my TV"; find.Location = new Point(523, 218); find.Size = new Size(150, 36);
            find.Click += async (sender, e) => await Work("find"); Controls.Add(find);
            faster.Text = "Shorter system animations (optional)"; faster.Location = new Point(30, 267); faster.Size = new Size(450, 30);
            Controls.Add(faster);
            install.Text = "Install Clear Home"; install.Location = new Point(30, 310); install.Size = new Size(230, 44);
            install.BackColor = Color.FromArgb(33, 76, 135); install.ForeColor = Color.White;
            install.FlatStyle = FlatStyle.Flat; install.Click += async (sender, e) => await Work("install"); Controls.Add(install);
            undo.Text = "Undo setup"; undo.Location = new Point(274, 310); undo.Size = new Size(150, 44);
            undo.Click += async (sender, e) => await Work("restore"); Controls.Add(undo);
            cancel.Text = "Cancel"; cancel.Location = new Point(641, 310); cancel.Size = new Size(150, 44); cancel.Enabled = false;
            cancel.Click += (sender, e) => { if (cancellation != null) cancellation.Cancel(); }; Controls.Add(cancel);
            status.Text = "Ready. Enter the TV address, or let setup find it."; status.Location = new Point(30, 369); status.Size = new Size(760, 28);
            Controls.Add(status);
            progress.Location = new Point(30, 402); progress.Size = new Size(760, 7); Controls.Add(progress);
            log.Location = new Point(30, 423); log.Size = new Size(760, 137); log.Multiline = true; log.ReadOnly = true;
            log.ScrollBars = ScrollBars.Vertical; log.Font = new Font("Consolas", 9); log.BackColor = Color.White; Controls.Add(log);
            var notices = new Label { Text = "The linked Python and Android SDK license terms apply to any automatically downloaded tools.\r\n"
                + "Tools and recovery backups stay in your Windows user folder. Your PATH and global Python are unchanged.",
                Location = new Point(30, 573), Size = new Size(760, 40), Font = new Font("Segoe UI", 8) };
            Controls.Add(notices);
            AddLink("Instructions", 30, "https://github.com/Er-Arif/clear-home-fire-tv#quick-start");
            AddLink("Python license", 155, "https://docs.python.org/3/license.html");
            AddLink("Android SDK terms", 293, "https://developer.android.com/studio/terms");
            if (preview) { status.Text = "Preview only - downloads and TV changes are disabled."; install.Enabled = find.Enabled = undo.Enabled = false; }
            FormClosing += (sender, e) => {
                if (cancellation != null) {
                    cancellation.Cancel(); e.Cancel = true;
                    status.Text = "Stopping safely. Keep the recovery backup if setup had started.";
                }
            };
        }
        private void AddLink(string label, int x, string url) {
            var link = new LinkLabel { Text = label, Location = new Point(x, 620), AutoSize = true, Font = new Font("Segoe UI", 9) };
            link.LinkClicked += (sender, e) => {
                try { Process.Start(new ProcessStartInfo(url) { UseShellExecute = true }); }
                catch (Exception) { Append("Open this link in your browser: " + url); }
            };
            Controls.Add(link);
        }
        private void Append(string message) {
            if (IsDisposed) return;
            log.AppendText(message + Environment.NewLine);
            log.SelectionStart = log.TextLength; log.ScrollToCaret();
        }
        private void Busy(bool value) {
            install.Enabled = find.Enabled = undo.Enabled = address.Enabled = faster.Enabled = !value && !preview;
            cancel.Enabled = value;
            progress.Style = value ? ProgressBarStyle.Marquee : ProgressBarStyle.Blocks;
            progress.MarqueeAnimationSpeed = value ? 25 : 0;
        }
        internal static List<string> ParseDevices(string mdns, string connected) {
            var found = new List<string>();
            foreach (string line in mdns.Split('\n')) {
                if (!(line.Contains("_adb._tcp") || line.Contains("_adb-tls-connect._tcp"))) continue;
                Match match = Regex.Match(line.Trim(), @"(?:^|\s)([A-Za-z0-9.-]+:\d{1,5})$");
                if (match.Success && !found.Contains(match.Groups[1].Value)) found.Add(match.Groups[1].Value);
            }
            foreach (Match match in Regex.Matches(connected, @"(?m)^([A-Za-z0-9.-]+:\d{1,5})\s+(?:device|unauthorized|offline)\b"))
                if (!found.Contains(match.Groups[1].Value)) found.Add(match.Groups[1].Value);
            // Prefer the ordinary ADB endpoint when a TV advertises a TLS endpoint as well.
            var result = new List<string>();
            foreach (string endpoint in found) {
                string host = endpoint.Substring(0, endpoint.LastIndexOf(':'));
                if (!endpoint.EndsWith(":5555", StringComparison.Ordinal) && found.Contains(host + ":5555")) continue;
                result.Add(endpoint);
            }
            return result;
        }
        private async Task<List<string>> Discover(IProgress<string> reporter, CancellationToken token) {
            reporter.Report("Looking for ADB-advertising TVs on your local network...");
            var mdns = await ProcessRunner.Run(tools.Adb, new [] { "mdns", "services" }, null, token, 15);
            var connected = await ProcessRunner.Run(tools.Adb, new [] { "devices" }, null, token, 15);
            return ParseDevices(mdns.Output, connected.Output);
        }
        private async Task Work(string action) {
            if (cancellation != null || preview) return;
            cancellation = new CancellationTokenSource(); Busy(true); log.Clear();
            var reporter = new Progress<string>(line => { status.Text = line.Length > 115 ? line.Substring(0, 112) + "..." : line; Append(line); });
            try {
                if (tools == null) tools = await new ToolsManager(home, payload).Prepare(reporter, cancellation.Token);
                if (action == "find" || string.IsNullOrWhiteSpace(address.Text)) {
                    var devices = await Discover(reporter, cancellation.Token);
                    address.Items.Clear(); foreach (string item in devices) address.Items.Add(item);
                    if (devices.Count == 1) address.Text = devices[0];
                    if (action == "find" || devices.Count != 1) {
                        status.Text = devices.Count == 0 ? "No TV advertised ADB. Enter its address from My Fire TV > About > Network."
                            : devices.Count == 1 ? "TV address found. Select Install Clear Home to continue." : "Choose your TV address from the list, then select Install.";
                        return;
                    }
                }
                string endpoint = address.Text.Trim();
                if (!Regex.IsMatch(endpoint, @"^[A-Za-z0-9.-]+:\d{1,5}$"))
                    throw new ArgumentException("Enter an IP:port address such as 192.168.1.50:5555. The TV address stays on your PC.");
                var arguments = new List<string> { "-I", "-u", Path.Combine(payload, "setup.py"), action, "--device", endpoint,
                    "--adb", tools.Adb, "--state-dir", Path.Combine(home, "State"), "--wait-for-authorization" };
                if (action == "install" && faster.Checked) arguments.Add("--faster-animations");
                var run = await ProcessRunner.Run(tools.Python, arguments, reporter, cancellation.Token, 600);
                if (run.ExitCode != 0) throw new InvalidOperationException("Setup stopped. Read the message below, correct the issue and try again. Your first recovery backup is kept.");
                status.Text = action == "install" ? "Installed. On the TV, choose Clear Home in Home on Fire, then press Home."
                    : "Setup changes restored. See the log if Home on Fire was already in use.";
            } catch (OperationCanceledException) {
                status.Text = cancellation.IsCancellationRequested ? "Canceled. Any recorded TV changes can be restored with Undo setup."
                    : "A download timed out. Check your connection and try again.";
            } catch (Exception error) {
                status.Text = "Setup needs attention. No unverified download will be run.";
                Append(error.Message);
            } finally {
                cancellation.Dispose(); cancellation = null; Busy(false);
            }
        }
    }
}
