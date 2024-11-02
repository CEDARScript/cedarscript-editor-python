# Copyright 2016 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""CLI Backend for the Analyzer Part of the Debugger.

The analyzer performs post hoc analysis of dumped intermediate tensors and
graph structure information from debugged Session.run() calls.
"""

def _make_source_table(source_list, is_tf_py_library):
    lines=[]
    return debugger_cli_common.rich_text_lines_from_rich_line_list(lines)
class DebugAnalyzer(object):
    def print_source(self, args, screen_info=None):
        pass
    def list_source(self, args, screen_info=None):
        output = []
        source_list = []
        output.extend(_make_source_table(
            [item for item in source_list if not item[1]], False))
        output.extend(_make_source_table(
            [item for item in source_list if item[1]], True))
        _add_main_menu(output, node_name=None)
        return output
