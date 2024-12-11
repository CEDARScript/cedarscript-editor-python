(function_declaration
  (comment)? @function.docstring
  (modifiers (annotation) )* @function.decorator
  (receiver_type: (type_reference))? @function.receiver
  (comment)? @function.docstring
  {definition_base}
  (type_parameters: (type_parameters))? @function.type_parameters
  body: (function_body) @function.body
) @function.definition

; Constructor definitions
(constructor_declaration
  (modifiers (annotation) )* @function.decorator
  (comment)? @function.docstring
  body: (function_body) @function.body
) @function.definition

; Lambda expressions
(lambda_literal
  body: (_) @function.body
) @function.definition