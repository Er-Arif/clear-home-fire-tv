using System;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;

namespace ClearHomeSetup {
    internal static class Payload {
        internal static string Hash(Stream stream) {
            using (var sha = SHA256.Create()) {
                return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
            }
        }
        internal static string HashFile(string path) {
            using (var input = File.OpenRead(path)) return Hash(input);
        }
        internal static void Verify(string path, string expected) {
            if (!System.Text.RegularExpressions.Regex.IsMatch(expected ?? "", "^[a-f0-9]{64}$") ||
                    !string.Equals(HashFile(path), expected, StringComparison.Ordinal))
                throw new InvalidDataException("Download checksum mismatch. The file will not be run.");
        }
        internal static void NoLinks(string path) {
            var current = new DirectoryInfo(path);
            while (current != null) {
                if (current.Exists && (current.Attributes & FileAttributes.ReparsePoint) != 0)
                    throw new InvalidDataException("Setup refuses a redirected folder: " + current.FullName);
                current = current.Parent;
            }
        }
        internal static void Extract(Stream input, string destination) {
            string root = Path.GetFullPath(destination).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            NoLinks(root);
            Directory.CreateDirectory(root);
            using (var archive = new ZipArchive(input, ZipArchiveMode.Read, true)) {
                long size = 0;
                foreach (var entry in archive.Entries) {
                    string relative = entry.FullName.Replace('/', Path.DirectorySeparatorChar);
                    if (Path.IsPathRooted(relative) || relative.IndexOf(':') >= 0)
                        throw new InvalidDataException("Unsafe archive entry.");
                    string target = Path.GetFullPath(Path.Combine(root, relative));
                    if (!target.StartsWith(root, StringComparison.OrdinalIgnoreCase))
                        throw new InvalidDataException("Archive entry escapes the setup folder.");
                    size += entry.Length;
                    if (size > 300L * 1024 * 1024) throw new InvalidDataException("Archive is too large.");
                    if (string.IsNullOrEmpty(entry.Name)) { NoLinks(target); Directory.CreateDirectory(target); continue; }
                    NoLinks(Path.GetDirectoryName(target));
                    if (File.Exists(target) && (File.GetAttributes(target) & FileAttributes.ReparsePoint) != 0)
                        throw new InvalidDataException("Setup refuses a redirected file.");
                    Directory.CreateDirectory(Path.GetDirectoryName(target));
                    using (var source = entry.Open())
                    using (var output = new FileStream(target, FileMode.Create, FileAccess.Write, FileShare.None))
                        source.CopyTo(output);
                }
            }
        }
        internal static bool MatchesArchive(Stream input, string destination) {
            string root = Path.GetFullPath(destination).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            if (!Directory.Exists(root)) return false;
            NoLinks(root);
            using (var archive = new ZipArchive(input, ZipArchiveMode.Read, true)) {
                foreach (var entry in archive.Entries) {
                    string relative = entry.FullName.Replace('/', Path.DirectorySeparatorChar);
                    if (Path.IsPathRooted(relative) || relative.IndexOf(':') >= 0) return false;
                    string target = Path.GetFullPath(Path.Combine(root, relative));
                    if (!target.StartsWith(root, StringComparison.OrdinalIgnoreCase)) return false;
                    if (string.IsNullOrEmpty(entry.Name)) continue;
                    NoLinks(Path.GetDirectoryName(target));
                    if (!File.Exists(target) || (File.GetAttributes(target) & FileAttributes.ReparsePoint) != 0) return false;
                    using (var expected = entry.Open()) if (Hash(expected) != HashFile(target)) return false;
                }
            }
            return true;
        }
        internal static string Prepare(string baseDirectory) {
            using (var resource = Assembly.GetExecutingAssembly().GetManifestResourceStream("ClearHome.Payload")) {
                if (resource == null) throw new InvalidDataException("Setup payload is missing.");
                string digest = Hash(resource);
                resource.Position = 0;
                string folder = Path.Combine(baseDirectory, "Setup", digest.Substring(0, 16));
                Extract(resource, folder);
                if (File.Exists(Path.Combine(folder, "TEST_ONLY")))
                    throw new InvalidDataException("This is a CI test build, not a release installer.");
                return folder;
            }
        }
    }
}
