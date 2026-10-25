using System;
using System.IO;
using System.Threading;
using System.Windows.Forms;

namespace ClearHomeSetup {
    internal static class Program {
        [STAThread]
        private static int Main(string[] args) {
            try {
                if (args.Length == 2 && args[0] == "--test-echo") {
                    Console.WriteLine(Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes(args[1]))); return 0;
                }
                if (args.Length == 1 && args[0] == "--test-sleep") { Thread.Sleep(10000); return 0; }
                if (args.Length == 2 && args[0] == "--self-test") return SelfTests.Run(Path.GetFullPath(args[1]));
                bool preview = args.Length > 0 && args[0] == "--preview";
                string home = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ClearHome");
                if (preview && args.Length == 2) home = Path.GetFullPath(args[1]);
                if (args.Length == 2 && args[0] == "--prepare-test") {
                    home = Path.GetFullPath(args[1]);
                    string testPayload = Payload.Prepare(home);
                    var manager = new ToolsManager(home, testPayload) { ForcePrivate = true };
                    object logGate = new object();
                    var reporter = new Progress<string>(line => { lock (logGate) File.AppendAllText(Path.Combine(home, "prepare.log"), line + Environment.NewLine); });
                    var prepared = manager.Prepare(reporter, CancellationToken.None).GetAwaiter().GetResult();
                    File.WriteAllText(Path.Combine(home, "prepared.txt"), prepared.Python + Environment.NewLine + prepared.Adb);
                    return 0;
                }
                bool created;
                string user = System.Security.Principal.WindowsIdentity.GetCurrent().User.Value;
                using (var mutex = new Mutex(true, @"Local\ClearHomeSetup-" + user, out created)) {
                    if (!created) { MessageBox.Show("Clear Home setup is already open.", "Clear Home"); return 1; }
                    string payload = Payload.Prepare(home);
                    Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
                    Application.Run(new MainForm(home, payload, preview));
                }
                return 0;
            } catch (Exception error) {
                if (args.Length == 2 && args[0] == "--prepare-test") {
                    Directory.CreateDirectory(Path.GetFullPath(args[1]));
                    File.WriteAllText(Path.Combine(Path.GetFullPath(args[1]), "error.txt"), error.ToString());
                } else MessageBox.Show(error.Message, "Clear Home setup", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 1;
            }
        }
    }
}
