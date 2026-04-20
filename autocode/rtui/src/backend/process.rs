#[allow(dead_code)]
use portable_pty::ExitStatus;

#[allow(dead_code)]
pub struct ChildGuard {
    child: Option<Box<dyn portable_pty::Child + Send>>,
    master: Option<Box<dyn portable_pty::MasterPty + Send>>,
}

impl ChildGuard {
    #[allow(dead_code)]
    pub fn new(child: Box<dyn portable_pty::Child + Send>) -> Self {
        Self {
            child: Some(child),
            master: None,
        }
    }

    #[allow(dead_code)]
    pub fn with_master(
        child: Box<dyn portable_pty::Child + Send>,
        master: Box<dyn portable_pty::MasterPty + Send>,
    ) -> Self {
        Self {
            child: Some(child),
            master: Some(master),
        }
    }

    #[allow(dead_code)]
    pub fn try_wait(&mut self) -> anyhow::Result<Option<ExitStatus>> {
        if let Some(ref mut child) = self.child {
            Ok(child.try_wait()?)
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
        if let Some(ref master) = self.master {
            master.resize(size)?;
        }
        Ok(())
    }
}

impl Drop for ChildGuard {
    fn drop(&mut self) {
        self.kill();
        if let Some(ref mut child) = self.child {
            let _ = child.wait();
        }
    }
}
