; Common pattern for body and docstring capture
body: (block
    .
    (expression_statement
        (string) @{type}.docstring)?
 ) @{type}.body
