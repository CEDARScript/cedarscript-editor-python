import functools


class SpyderKernel(IPythonKernel):
    """Spyder kernel for Jupyter."""

    shell_class = SpyderShell
    @comm_handler
    def safe_exec(self, filename):
        """Safely execute a file using IPKernelApp._exec_file."""
        self.parent._exec_file(filename)

    @comm_handler
    @functools.lru_cache(32)
    def get_fault_text(self, fault_filename, main_id, ignore_ids):
        """Get fault text from old run."""
        # Read file
        try:
            with open(fault_filename, 'r') as f:
                fault = f.read()
        except FileNotFoundError:
            return
        return text

    def get_system_threads_id(self):
        """Return the list of system threads id."""
        ignore_threads = [
        ]
