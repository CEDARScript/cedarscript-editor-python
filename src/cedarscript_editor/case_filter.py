from typing import Optional, Sequence
from cedarscript_ast_parser import CaseStatement, CaseWhen, CaseAction, LoopControl


# <dt>case_stmt: CASE WHEN (EMPTY | REGEX r"<string>" | PREFIX "<string>" | SUFFIX "<string>" | INDENT LEVEL <integer> | LINE NUMBER <integer> ) \
# THEN (CONTINUE | BREAK | REMOVE [BREAK] | INDENT <integer> [BREAK] | REPLACE r"<string>" [BREAK] | <content_literal> [BREAK] | <content_from_segment> [BREAK])</dt>
# <dd>This is the versatile `WHEN..THEN` content filter. Only used in conjunction with <replace_region_clause>. \
# Filters each line of the region according to `WHEN/THEN` pairs:</dd>
# <dd>WHEN: Allows you to choose which *matcher* to use:</dd>
# <dd>EMPTY: Matches an empty line</dd>
# <dd>REGEX: Regex matcher. Allows using capture groups in the `REPLACE` action</dd>
# <dd>PREFIX: Matches by line prefix</dd>
# <dd>SUFFIX: Matches by line suffix</dd>
# <dd>INDENT LEVEL: Matches lines with specific indent level</dd>
# <dd>LINE NUMBER: Matches by line number</dd>
# <dd>THEN: Allows you to choose which *action* to take for its matched line:</dd>
# <dd>CONTINUE: Leaves the line as is and goes to the next</dd>
# <dd>BREAK: Stops processing the lines, leaving the rest of the lines untouched</dd>
# <dd>REMOVE: Removes the line</dd>
# <dd>INDENT: Increases or decreases indent level. Only positive or negative integers</dd>
# <dd>REPLACE: Replace with text (regex capture groups enabled: \\1, \\2, etc)</dd>
# <dd><content_literal> or <content_from_segment>: Replace with text (can't use regex capture groups)</dd>
# <dt>


def process_case_statement(content: Sequence[str], case_statement: CaseStatement) -> list[str]:
    """Process content lines according to CASE statement rules.
    
    Args:
        content: Sequence of strings to process
        case_statement: CaseStatement containing when/then rules
        
    Returns:
        List of processed strings
    """
    result = []
    
    for line_num, line in enumerate(content, start=1):
        indent_level = (len(line) - len(line.lstrip())) // 4
        matched = False
        
        # Process each when/then pair
        for when, action in case_statement.cases:
            if _matches_when(line, when, indent_level, line_num):
                matched = True
                processed = _apply_action(line, action, indent_level, when)
                
                if processed is None:  # REMOVE action
                    break
                if isinstance(processed, LoopControl):
                    if processed == LoopControl.BREAK:
                        result.append(line)
                        result.extend(content[line_num:])
                        return result
                    elif processed == LoopControl.CONTINUE:
                        result.append(line)
                        break
                else:
                    result.append(processed)
                break
        
        # If no when conditions matched, use else action if present
        if not matched and case_statement.else_action is not None:
            processed = _apply_action(line, case_statement.else_action, indent_level, None)
            if processed is not None and not isinstance(processed, LoopControl):
                result.append(processed)
        elif not matched:
            result.append(line)
            
    return result

def _matches_when(line: str, when: CaseWhen, indent_level: int, line_num: int) -> bool:
    """Check if a line matches the given when condition."""
    stripped = line.strip()
    if when.empty and not stripped:
        return True
    if when.regex and when.regex.search(stripped):
        return True
    if when.prefix and stripped.startswith(when.prefix.strip()):
        return True
    if when.suffix and stripped.endswith(when.suffix.strip()):
        return True
    if when.indent_level is not None and indent_level == when.indent_level:
        return True
    if when.line_number is not None and line_num == when.line_number:
        return True
    return False


def _apply_action(line: str, action: CaseAction, current_indent: int, when: CaseWhen) -> Optional[str | LoopControl]:
    """Apply the given action to a line.
    
    Returns:
        - None for REMOVE action
        - LoopControl enum for BREAK/CONTINUE
        - Modified string for other actions
    """
    if action.loop_control:
        return action.loop_control
    if action.remove:
        return None
    if action.indent is not None:
        new_indent = current_indent + action.indent
        if new_indent < 0:
            new_indent = 0
        return " " * (new_indent * 4) + line.lstrip()
    if action.sub_pattern is not None:
        line = action.sub_pattern.sub(action.sub_repl, line)
    if action.content is not None:
        if isinstance(action.content, str):
            # TODO
            return " " * (current_indent * 4) + action.content
        else:
            region, indent = action.content
            # TODO Handle region content replacement - would need region processing logic
            return line
    return line
