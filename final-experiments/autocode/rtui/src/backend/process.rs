#[derive(Debug, Clone)]
pub struct BackendExitStatus {
    code: i32,
}

impl BackendExitStatus {
    pub fn from_exit_code(code: i32) -> Self {
        Self { code }
    }

    pub fn success(&self) -> bool {
        self.code == 0
    }

    pub fn exit_code(&self) -> i32 {
        self.code
    }
}

pub struct BackendProcessGuard {
    child: Option<std::process::Child>,
}

impl BackendProcessGuard {
    pub fn from_optional(child: Option<std::process::Child>) -> Self {
        Self { child }
    }

    pub fn try_wait(&mut self) -> anyhow::Result<Option<BackendExitStatus>> {
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

    pub fn kill(&mut self) {
        if let Some(ref mut child) = self.child {
            let _ = child.kill();
        }
    }
}

fn convert_exit_status(status: std::process::ExitStatus) -> BackendExitStatus {
    if let Some(code) = status.code() {
        return BackendExitStatus::from_exit_code(code);
    }

    #[cfg(unix)]
    {
        use std::os::unix::process::ExitStatusExt;

        if let Some(signal) = status.signal() {
            return BackendExitStatus::from_exit_code(128 + signal);
        }
    }

    BackendExitStatus::from_exit_code(1)
}

impl Drop for BackendProcessGuard {
    fn drop(&mut self) {
        self.kill();
        if let Some(ref mut child) = self.child {
            let _ = child.wait();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{BackendExitStatus, BackendProcessGuard};

    #[test]
    fn backend_exit_status_exposes_success_and_code_without_pty_dependency() {
        let ok = BackendExitStatus::from_exit_code(0);
        let failed = BackendExitStatus::from_exit_code(17);

        assert!(ok.success());
        assert_eq!(ok.exit_code(), 0);
        assert!(!failed.success());
        assert_eq!(failed.exit_code(), 17);
    }

    #[test]
    fn backend_process_guard_accepts_attach_mode_without_child() {
        let mut guard = BackendProcessGuard::from_optional(None);

        assert!(guard.try_wait().unwrap().is_none());
    }
}
