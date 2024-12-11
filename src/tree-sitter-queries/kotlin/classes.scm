; Regular class definitions with optional annotations and KDoc
(class_declaration
  (modifiers (annotation) )* @class.decorator
  (comment)? @class.docstring
  ["data" "enum"]? @class.subtype
  {definition_base}
  body: (class_body) @class.body
) @class.definition

; Interface definitions
(interface_declaration
  (modifiers (annotation) @class.decorator)*
  (comment)? @class.docstring
  name: (type_identifier) @_class_name
  (#match? @_class_name "^{{name}}$")
  (#set! role name)
  body: (class_body) @class.body
) @class.definition

; Object declarations
(object_declaration
  (modifiers (annotation) @class.decorator)*
  (comment)? @class.docstring
  name: (type_identifier) @_class_name
  (#match? @_class_name "^{{name}}$")
  (#set! role name)
  body: (class_body) @class.body
) @class.definition
