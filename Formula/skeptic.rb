# Homebrew formula for Skeptic.
#   brew tap danieljcuesta007/skeptic https://github.com/danieljcuesta007/skeptic
#   brew install skeptic
# scripts/release.sh fills in url and sha256 for each release.
class Skeptic < Formula
  desc "Switch AI coding agents mid-task without losing your work"
  homepage "https://skeptic.pages.dev"
  url "https://github.com/danieljcuesta007/skeptic/releases/download/v0.1.0/skeptic-0.1.0.tar.gz"
  sha256 "9988c22478bf3a9ea4cbed29e949e07320bc89401b7f234b8bf3f4e5dbdd22bf"
  license "MIT"

  depends_on "python@3.13"
  uses_from_macos "git"

  def install
    libexec.install Dir["*"]
    python = Formula["python@3.13"].opt_bin/"python3.13"
    (bin/"skeptic").write <<~SH
      #!/bin/sh
      exec "#{python}" -B "#{opt_libexec}/apps/terminal/switcher.py" "$@"
    SH
    (bin/"skeptic-setup").write <<~SH
      #!/bin/sh
      # Adds the /skeptic helpers for Claude Code and Codex. Touches nothing else.
      exec "#{python}" -B "#{opt_libexec}/apps/terminal/install.py" --skills-only --upgrade-integrations "$@"
    SH
  end

  def caveats
    <<~EOS
      One more step, so /skeptic works inside Claude Code and Codex:
        skeptic-setup
      Then, in any project:
        skeptic
    EOS
  end

  test do
    assert_match "continue", shell_output("#{bin}/skeptic --help")
  end
end
