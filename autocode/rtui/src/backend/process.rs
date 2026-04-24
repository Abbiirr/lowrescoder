#[allow(dead_code)]
use portable_pty::ExitStatus;

#[allow(dead_code)]
pub struct ChildGuard {
    child: Option<std::process::Child>,
}

impl ChildGuard {
    #[allow(dead_code)]
    pub fn new(child: std::process::Child) -> Self {
        Self { child: Some(child) }
    }

    #[allow(dead_code)]
    pub fn from_optional(child: Option<std::process::Child>) -> Self {
        Self { child }
    }

    #[allow(dead_code)]
    pub fn try_wait(&mut self) -> anyhow::Result<Option<ExitStatus>> {
        if let Some(mut child) = self.child.take() {
            match child.try_wait()? {
                Some(status) => Ok(Some(convert_exit_status(status))),
                None => {
                    self.child = Some(child);
                    Ok(None)
                }
            }
        } else {
            Ok(None)
        }
    }

    #[allow(dead_code)]
    pub fn kill(&mut self) {
        if let Some(ref mut child) = self.child {
            let _ = child.kill();
        }
    }

    #[allow(dead_code)]
    pub fn resize(&self, size: portable_pty::PtySize) -> anyhow::Result<()> {
        let _ = size;
        Ok(())
    }
}

fn convert_exit_status(status: std::process::ExitStatus) -> ExitStatus {
    if let Some(code) = status.code() {
        return ExitStatus::with_exit_code(code as u32);
    }

    #[cfg(unix)]
    {
        use std::os::unix::process::ExitStatusExt;

        if let Some(signal) = status.signal() {
            return ExitStatus::with_signal(&format!("signal {}", signal));
        }
    }

    ExitStatus::with_exit_code(1)
}

impl Drop for ChildGuard {
    fn drop(&mut self) {
        self.kill();
        if let Some(ref mut child) = self.child {
            let _ = child.wait();
        }
    }
}
