@comm_handler
def get_fault_text(fault_filename, main_id, ignore_ids):
    """Get fault text from old run."""
    # Read file
    try:
        with open(fault_filename, 'r') as f:
            fault = f.read()
    except FileNotFoundError:
        return
    return text
class SpyderKernel(IPythonKernel):
    """Spyder kernel for Jupyter."""

    shell_class = SpyderShell
    @comm_handler
    def safe_exec(self, filename):
        """Safely execute a file using IPKernelApp._exec_file."""
        self.parent._exec_file(filename)


    def get_system_threads_id(self):
        """Return the list of system threads id."""
        ignore_threads = [
        ]
