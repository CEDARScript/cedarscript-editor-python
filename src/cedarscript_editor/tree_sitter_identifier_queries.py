# # Credits
# 
# CEDARScript uses modified versions of the tags.scm files from these open source
# tree-sitter language implementations:
# 
# * [https://github.com/tree-sitter/tree-sitter-c](https://github.com/tree-sitter/tree-sitter-c) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-c-sharp](https://github.com/tree-sitter/tree-sitter-c-sharp) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-cpp](https://github.com/tree-sitter/tree-sitter-cpp) — licensed under the MIT License.
# * [https://github.com/Wilfred/tree-sitter-elisp](https://github.com/Wilfred/tree-sitter-elisp) — licensed under the MIT License.
# * [https://github.com/elixir-lang/tree-sitter-elixir](https://github.com/elixir-lang/tree-sitter-elixir) — licensed under the Apache License, Version 2.0.
# * [https://github.com/elm-tooling/tree-sitter-elm](https://github.com/elm-tooling/tree-sitter-elm) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-go](https://github.com/tree-sitter/tree-sitter-go) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-java](https://github.com/tree-sitter/tree-sitter-java) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-javascript](https://github.com/tree-sitter/tree-sitter-javascript) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-ocaml](https://github.com/tree-sitter/tree-sitter-ocaml) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-php](https://github.com/tree-sitter/tree-sitter-php) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-python](https://github.com/tree-sitter/tree-sitter-python) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-ql](https://github.com/tree-sitter/tree-sitter-ql) — licensed under the MIT License.
# * [https://github.com/r-lib/tree-sitter-r](https://github.com/r-lib/tree-sitter-r) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-ruby](https://github.com/tree-sitter/tree-sitter-ruby) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-rust](https://github.com/tree-sitter/tree-sitter-rust) — licensed under the MIT License.
# * [https://github.com/tree-sitter/tree-sitter-typescript](https://github.com/tree-sitter/tree-sitter-typescript) — licensed under the MIT License.

# query_scm = get_scm_fname(langstr)
# query_scm = query_scm.read_text()
# def get_scm_fname(langstr):
#     # Load the tags queries
#     try:
#         return resources.files(__package__).joinpath("queries", f"tree-sitter-{langstr}-tags.scm")
#     except KeyError:
#         return


LANG_TO_TREE_SITTER_QUERY = {
    "python": {
        'function': """
    ; Regular and async function definitions with optional docstring
    (function_definition
      name: (identifier) @_function_name
      (#match? @_function_name "^{name}$")
      body: (block) @function.body) @function.definition

    (function_definition
      name: (identifier) @_function_name
      (#match? @_function_name "^{name}$")
      body: (block
        .
        (expression_statement
          (string) @function.docstring)?
        .
        (_)*))

    ; Decorated function definitions (including async) with optional docstring
    (decorated_definition
      (decorator)+
      (function_definition
        name: (identifier) @_function_name
        (#match? @_function_name "^{name}$")
        body: (block) @function.body)) @function.definition

    (decorated_definition
      (decorator)+
      (function_definition
        name: (identifier) @_function_name
        (#match? @_function_name "^{name}$")
        body: (block
          .
          (expression_statement
            (string) @function.docstring)?
          .
          (_)*)))

    ; Method definitions in classes (including async and decorated) with optional docstring
    (class_definition
      body: (block
        (function_definition
          name: (identifier) @_function_name
          (#match? @_function_name "^{name}$")
          body: (block) @function.body) @function.definition))

    (class_definition
      body: (block
        (function_definition
          name: (identifier) @_function_name
          (#match? @_function_name "^{name}$")
          body: (block
            .
            (expression_statement
              (string) @function.docstring)?
            .
            (_)*))))
""",

        'class': """
    ; Regular and decorated class definitions (including nested) with optional docstring
    (class_definition
      name: (identifier) @_class_name
      (#match? @_class_name "^{name}$")
      body: (block) @class.body) @class.definition

    (class_definition
      name: (identifier) @_class_name
      (#match? @_class_name "^{name}$")
      body: (block
        .
        (expression_statement
          (string) @class.docstring)?
        .
        (_)*))

    ; Decorated class definitions
    (decorated_definition
      (decorator)+
      (class_definition
        name: (identifier) @_class_name
        (#match? @_class_name "^{name}$")
        body: (block) @class.body)) @class.definition

    (decorated_definition
      (decorator)+
      (class_definition
        name: (identifier) @_class_name
        (#match? @_class_name "^{name}$")
        body: (block
          .
          (expression_statement
            (string) @class.docstring)?
          .
          (_)*)))

    ; Nested class definitions within other classes
    (class_definition
      body: (block
        (class_definition
          name: (identifier) @_class_name
          (#match? @_class_name "^{name}$")
          body: (block) @class.body) @class.definition))

    (class_definition
      body: (block
        (class_definition
          name: (identifier) @_class_name
          (#match? @_class_name "^{name}$")
          body: (block
            .
            (expression_statement
              (string) @class.docstring)?
            .
            (_)*))))
"""
    },
    "kotlin": {
        'function': """
    ; Regular function definitions with optional annotations and KDoc
    (function_declaration
      (modifiers (annotation) @function.decorator)*
      name: (simple_identifier) @_function_name
      body: (function_body) @function.body) @function.definition

    (function_declaration
      (modifiers (annotation) @function.decorator)*
      (comment) @function.docstring
      name: (simple_identifier) @_function_name
      body: (function_body) @function.body) @function.definition

    ; Function definitions with type parameters
    (function_declaration
      (modifiers (annotation) @function.decorator)*
      name: (simple_identifier) @_function_name
      type_parameters: (type_parameters)
      body: (function_body) @function.body) @function.definition

    (function_declaration
      (modifiers (annotation) @function.decorator)*
      (comment) @function.docstring
      name: (simple_identifier) @_function_name
      type_parameters: (type_parameters)
      body: (function_body) @function.body) @function.definition

    ; Method definitions in classes
    (class_body
      (function_declaration
        (modifiers (annotation) @function.decorator)*
        name: (simple_identifier) @_function_name
        body: (function_body) @function.body) @function.definition)

    (class_body
      (function_declaration
        (modifiers (annotation) @function.decorator)*
        (comment) @function.docstring
        name: (simple_identifier) @_function_name
        body: (function_body) @function.body) @function.definition)

    ; Constructor definitions
    (class_body
      (constructor_declaration
        (modifiers (annotation) @function.decorator)*
        body: (function_body) @function.body) @function.definition)

    (class_body
      (constructor_declaration
        (modifiers (annotation) @function.decorator)*
        (comment) @function.docstring
        body: (function_body) @function.body) @function.definition)

    ; Extension functions
    (function_declaration
      (modifiers (annotation) @function.decorator)*
      receiver_type: (type_reference)
      name: (simple_identifier) @_function_name
      body: (function_body) @function.body) @function.definition

    (function_declaration
      (modifiers (annotation) @function.decorator)*
      (comment) @function.docstring
      receiver_type: (type_reference)
      name: (simple_identifier) @_function_name
      body: (function_body) @function.body) @function.definition

    ; Backticked function names
    (function_declaration
      (modifiers (annotation) @function.decorator)*
      name: (simple_identifier (identifier_string)) @_function_name
      body: (function_body) @function.body) @function.definition

    (function_declaration
      (modifiers (annotation) @function.decorator)*
      (comment) @function.docstring
      name: (simple_identifier (identifier_string)) @_function_name
      body: (function_body) @function.body) @function.definition

    ; Lambda expressions
    (lambda_literal
      body: (_) @function.body) @function.definition
    """,

        'class': """
    ; Regular class definitions with optional annotations and KDoc
    (class_declaration
      (modifiers (annotation) @class.decorator)*
      name: (type_identifier) @_class_name
      body: (class_body) @class.body) @class.definition

    (class_declaration
      (modifiers (annotation) @class.decorator)*
      (comment) @class.docstring
      name: (type_identifier) @_class_name
      body: (class_body) @class.body) @class.definition

    ; Interface definitions
    (interface_declaration
      (modifiers (annotation) @class.decorator)*
      name: (type_identifier) @_class_name
      body: (class_body) @class.body) @class.definition

    (interface_declaration
      (modifiers (annotation) @class.decorator)*
      (comment) @class.docstring
      name: (type_identifier) @_class_name
      body: (class_body) @class.body) @class.definition

    ; Object declarations
    (object_declaration
      (modifiers (annotation) @class.decorator)*
      name: (type_identifier) @_class_name
      body: (class_body) @class.body) @class.definition

    (object_declaration
      (modifiers (annotation) @class.decorator)*
      (comment) @class.docstring
      name: (type_identifier) @_class_name
      body: (class_body) @class.body) @class.definition

    ; Nested class definitions
    (class_body
      (class_declaration
        (modifiers (annotation) @class.decorator)*
        name: (type_identifier) @_class_name
        body: (class_body) @class.body) @class.definition)

    (class_body
      (class_declaration
        (modifiers (annotation) @class.decorator)*
        (comment) @class.docstring
        name: (type_identifier) @_class_name
        body: (class_body) @class.body) @class.definition)

    ; Data class definitions
    (class_declaration
      (modifiers (annotation) @class.decorator)*
      "data"
      name: (type_identifier) @_class_name
      body: (class_body) @class.body) @class.definition

    (class_declaration
      (modifiers (annotation) @class.decorator)*
      (comment) @class.docstring
      "data"
      name: (type_identifier) @_class_name
      body: (class_body) @class.body) @class.definition

    ; Enum class definitions
    (class_declaration
      (modifiers (annotation) @class.decorator)*
      "enum"
      name: (type_identifier) @_class_name
      body: (class_body) @class.body) @class.definition

    (class_declaration
      (modifiers (annotation) @class.decorator)*
      (comment) @class.docstring
      "enum"
      name: (type_identifier) @_class_name
      body: (class_body) @class.body) @class.definition
    """
    },

    "php": {
        'function': """
    ; Regular function definitions with optional attributes and docstring
    (function_definition
      (attribute_list)? @function.decorator
      name: (name) @function.name
      body: (compound_statement) @function.body) @function.definition

    (function_definition
      (attribute_list)? @function.decorator
      (comment) @function.docstring
      name: (name) @function.name
      body: (compound_statement) @function.body) @function.definition

    ; Method definitions in classes with optional attributes and docstring
    (method_declaration
      (attribute_list)? @function.decorator
      name: (name) @function.name
      body: (compound_statement) @function.body) @function.definition

    (method_declaration
      (attribute_list)? @function.decorator
      (comment) @function.docstring
      name: (name) @function.name
      body: (compound_statement) @function.body) @function.definition

    ; Anonymous functions
    (anonymous_function
      (attribute_list)? @function.decorator
      body: (compound_statement) @function.body) @function.definition

    ; Arrow functions
    (arrow_function
      (attribute_list)? @function.decorator
      body: (expression) @function.body) @function.definition
    """,

        'class': ("class.definition", "class.name", "class.body", "class.docstring", "class.decorator", """
    ; Regular class definitions with optional attributes and docstring
    (class_declaration
      (attribute_list)? @class.decorator
      name: (name) @class.name
      body: (declaration_list) @class.body) @class.definition

    (class_declaration
      (attribute_list)? @class.decorator
      (comment) @class.docstring
      name: (name) @class.name
      body: (declaration_list) @class.body) @class.definition

    ; Interface definitions
    (interface_declaration
      (attribute_list)? @class.decorator
      name: (name) @class.name
      body: (declaration_list) @class.body) @class.definition

    (interface_declaration
      (attribute_list)? @class.decorator
      (comment) @class.docstring
      name: (name) @class.name
      body: (declaration_list) @class.body) @class.definition

    ; Trait definitions
    (trait_declaration
      (attribute_list)? @class.decorator
      name: (name) @class.name
      body: (declaration_list) @class.body) @class.definition

    (trait_declaration
      (attribute_list)? @class.decorator
      (comment) @class.docstring
      name: (name) @class.name
      body: (declaration_list) @class.body) @class.definition

    ; Enum definitions
    (enum_declaration
      (attribute_list)? @class.decorator
      name: (name) @class.name
      body: (enum_declaration_list) @class.body) @class.definition

    (enum_declaration
      (attribute_list)? @class.decorator
      (comment) @class.docstring
      name: (name) @class.name
      body: (enum_declaration_list) @class.body) @class.definition
    """)
    },

    "rust": {
        'function': """
    ; Function definitions with optional attributes, visibility, and docstring
    (function_item
      (attribute_item)? @function.decorator
      (visibility_modifier)? 
      (function_modifiers)?
      "fn"
      name: (identifier) @function.name
      parameters: (parameters)
      return_type: (_)? 
      body: (block) @function.body) @function.definition

    (function_item
      (attribute_item)? @function.decorator
      (visibility_modifier)? 
      (function_modifiers)?
      (line_comment)+ @function.docstring
      "fn"
      name: (identifier) @function.name
      parameters: (parameters)
      return_type: (_)? 
      body: (block) @function.body) @function.definition

    ; Method definitions in impl blocks
    (impl_item
      (attribute_item)? @function.decorator
      (visibility_modifier)? 
      (function_modifiers)?
      "fn"
      name: (identifier) @function.name
      parameters: (parameters)
      return_type: (_)? 
      body: (block) @function.body) @function.definition

    (impl_item
      (attribute_item)? @function.decorator
      (visibility_modifier)? 
      (function_modifiers)?
      (line_comment)+ @function.docstring
      "fn"
      name: (identifier) @function.name
      parameters: (parameters)
      return_type: (_)? 
      body: (block) @function.body) @function.definition

    ; Async function definitions
    (function_item
      (attribute_item)? @function.decorator
      (visibility_modifier)? 
      "async"
      "fn"
      name: (identifier) @function.name
      parameters: (parameters)
      return_type: (_)? 
      body: (block) @function.body) @function.definition

    ; Const function definitions
    (function_item
      (attribute_item)? @function.decorator
      (visibility_modifier)? 
      "const"
      "fn"
      name: (identifier) @function.name
      parameters: (parameters)
      return_type: (_)? 
      body: (block) @function.body) @function.definition
    """,

        'class': ("class.definition", "class.name", "class.body", "class.docstring", "class.decorator", """
    ; Struct definitions with optional attributes, visibility, and docstring
    (struct_item
      (attribute_item)? @class.decorator
      (visibility_modifier)? 
      "struct"
      name: (type_identifier) @class.name
      body: (field_declaration_list)? @class.body) @class.definition

    (struct_item
      (attribute_item)? @class.decorator
      (visibility_modifier)? 
      (line_comment)+ @class.docstring
      "struct"
      name: (type_identifier) @class.name
      body: (field_declaration_list)? @class.body) @class.definition

    ; Enum definitions
    (enum_item
      (attribute_item)? @class.decorator
      (visibility_modifier)? 
      "enum"
      name: (type_identifier) @class.name
      body: (enum_variant_list) @class.body) @class.definition

    (enum_item
      (attribute_item)? @class.decorator
      (visibility_modifier)? 
      (line_comment)+ @class.docstring
      "enum"
      name: (type_identifier) @class.name
      body: (enum_variant_list) @class.body) @class.definition

    ; Trait definitions
    (trait_item
      (attribute_item)? @class.decorator
      (visibility_modifier)? 
      "trait"
      name: (type_identifier) @class.name
      body: (declaration_list) @class.body) @class.definition

    (trait_item
      (attribute_item)? @class.decorator
      (visibility_modifier)? 
      (line_comment)+ @class.docstring
      "trait"
      name: (type_identifier) @class.name
      body: (declaration_list) @class.body) @class.definition

    ; Union definitions
    (union_item
      (attribute_item)? @class.decorator
      (visibility_modifier)? 
      "union"
      name: (type_identifier) @class.name
      body: (field_declaration_list) @class.body) @class.definition

    (union_item
      (attribute_item)? @class.decorator
      (visibility_modifier)? 
      (line_comment)+ @class.docstring
      "union"
      name: (type_identifier) @class.name
      body: (field_declaration_list) @class.body) @class.definition
    """)
    },

    "go": {
        'function': """
    ; Function declarations with optional docstring
    (function_declaration
      (comment)* @function.docstring
      name: (identifier) @function.name
      body: (block) @function.body) @function.definition

    ; Method declarations with optional docstring
    (method_declaration
      (comment)* @function.docstring
      name: (field_identifier) @function.name
      body: (block) @function.body) @function.definition
    """,

        'class': ("class.definition", "class.name", "class.body", "class.docstring", "class.decorator", """
    ; Struct type definitions with optional docstring
    (type_declaration
      (type_spec
        name: (type_identifier) @class.name
        type: (struct_type
          (field_declaration_list) @class.body))) @class.definition

    (type_declaration
      (comment)* @class.docstring
      (type_spec
        name: (type_identifier) @class.name
        type: (struct_type
          (field_declaration_list) @class.body))) @class.definition

    ; Interface type definitions with optional docstring
    (type_declaration
      (type_spec
        name: (type_identifier) @class.name
        type: (interface_type
          (method_spec_list) @class.body))) @class.definition

    (type_declaration
      (comment)* @class.docstring
      (type_spec
        name: (type_identifier) @class.name
        type: (interface_type
          (method_spec_list) @class.body))) @class.definition
    """)
    },

    "cpp": {
        'function': """
    ; Function definitions
    (function_definition
      declarator: (function_declarator
        declarator: (identifier) @function.name) 
      body: (compound_statement) @function.body) @function.definition

    ; Method definitions
    (function_definition
      declarator: (function_declarator
        declarator: (field_identifier) @function.name)
      body: (compound_statement) @function.body) @function.definition

    ; Constructor definitions
    (constructor_or_destructor_definition
      declarator: (function_declarator
        declarator: (qualified_identifier
          name: (identifier) @function.name))
      body: (compound_statement) @function.body) @function.definition

    ; Destructor definitions
    (constructor_or_destructor_definition
      declarator: (function_declarator
        declarator: (destructor_name
          (identifier) @function.name))
      body: (compound_statement) @function.body) @function.definition

    ; Operator overloading definitions
    (function_definition
      declarator: (function_declarator
        declarator: (operator_name) @function.name)
      body: (compound_statement) @function.body) @function.definition

    ; Lambda expressions
    (lambda_expression
      body: (compound_statement) @function.body) @function.definition
    """,

        'class': ("class.definition", "class.name", "class.body", "class.docstring", "class.decorator", """
    ; Class definitions
    (class_specifier
      name: (type_identifier) @class.name
      body: (field_declaration_list) @class.body) @class.definition

    ; Struct definitions
    (struct_specifier
      name: (type_identifier) @class.name
      body: (field_declaration_list) @class.body) @class.definition

    ; Union definitions
    (union_specifier
      name: (type_identifier) @class.name
      body: (field_declaration_list) @class.body) @class.definition

    ; Enum definitions
    (enum_specifier
      name: (type_identifier) @class.name
      body: (enumerator_list) @class.body) @class.definition

    ; Template class definitions
    (template_declaration
      (class_specifier
        name: (type_identifier) @class.name
        body: (field_declaration_list) @class.body)) @class.definition

    ; Template struct definitions
    (template_declaration
      (struct_specifier
        name: (type_identifier) @class.name
        body: (field_declaration_list) @class.body)) @class.definition
    """)
    },

    "c": {
        'function': """
    ; Function definitions
    (function_definition
      declarator: (function_declarator
        declarator: (identifier) @function.name)
      body: (compound_statement) @function.body) @function.definition

    ; Function definitions with type qualifiers
    (function_definition
      type: (type_qualifier)
      declarator: (function_declarator
        declarator: (identifier) @function.name)
      body: (compound_statement) @function.body) @function.definition

    ; Function declarations (prototypes)
    (declaration
      declarator: (function_declarator
        declarator: (identifier) @function.name)) @function.definition
    """,

        'class': ("class.definition", "class.name", "class.body", "class.docstring", "class.decorator", """
    ; Struct definitions
    (struct_specifier
      name: (type_identifier) @class.name
      body: (field_declaration_list) @class.body) @class.definition

    ; Union definitions
    (union_specifier
      name: (type_identifier) @class.name
      body: (field_declaration_list) @class.body) @class.definition

    ; Enum definitions
    (enum_specifier
      name: (type_identifier) @class.name
      body: (enumerator_list) @class.body) @class.definition

    ; Typedef struct definitions
    (declaration
      (type_qualifier)*
      "typedef"
      (type_qualifier)*
      (struct_specifier
        name: (type_identifier) @class.name
        body: (field_declaration_list) @class.body)
      (type_identifier)) @class.definition

    ; Typedef union definitions
    (declaration
      (type_qualifier)*
      "typedef"
      (type_qualifier)*
      (union_specifier
        name: (type_identifier) @class.name
        body: (field_declaration_list) @class.body)
      (type_identifier)) @class.definition

    ; Typedef enum definitions
    (declaration
      (type_qualifier)*
      "typedef"
      (type_qualifier)*
      (enum_specifier
        name: (type_identifier) @class.name
        body: (enumerator_list) @class.body)
      (type_identifier)) @class.definition
    """)
    },

    "java": {
        'function': """
    ; Method declarations
    (method_declaration
      (modifiers)? @function.decorator
      (_method_header
        name: (identifier) @function.name)
      body: (block) @function.body) @function.definition

    ; Compact constructor declarations (for records)
    (compact_constructor_declaration
      (modifiers)? @function.decorator
      name: (identifier) @function.name
      body: (block) @function.body) @function.definition

    ; Constructor declarations
    (constructor_declaration
      (modifiers)? @function.decorator
      (_constructor_declarator
        name: (identifier) @function.name)
      body: (constructor_body) @function.body) @function.definition
    """,

        'class': ("class.definition", "class.name", "class.body", "class.docstring", "class.decorator", """
    ; Class declarations
    (class_declaration
      (modifiers)? @class.decorator
      "class"
      name: (identifier) @class.name
      body: (class_body) @class.body) @class.definition

    ; Interface declarations
    (interface_declaration
      (modifiers)? @class.decorator
      "interface"
      name: (identifier) @class.name
      body: (interface_body) @class.body) @class.definition

    ; Enum declarations
    (enum_declaration
      (modifiers)? @class.decorator
      "enum"
      name: (identifier) @class.name
      body: (enum_body) @class.body) @class.definition

    ; Record declarations
    (record_declaration
      (modifiers)? @class.decorator
      "record"
      name: (identifier) @class.name
      body: (class_body) @class.body) @class.definition

    ; Annotation type declarations
    (annotation_type_declaration
      (modifiers)? @class.decorator
      "@interface"
      name: (identifier) @class.name
      body: (annotation_type_body) @class.body) @class.definition
    """)
    },

    "javascript": {
        'function': """
    ; Function declarations
    (function_declaration
      name: (identifier) @function.name
      body: (statement_block) @function.body) @function.definition

    ; Function expressions
    (function_expression
      name: (identifier)? @function.name
      body: (statement_block) @function.body) @function.definition

    ; Arrow functions
    (arrow_function
      body: [(expression) (statement_block)] @function.body) @function.definition

    ; Method definitions
    (method_definition
      name: [(property_identifier) (private_property_identifier)] @function.name
      body: (statement_block) @function.body) @function.definition

    ; Generator functions
    (generator_function_declaration
      name: (identifier) @function.name
      body: (statement_block) @function.body) @function.definition

    (generator_function
      name: (identifier)? @function.name
      body: (statement_block) @function.body) @function.definition

    ; Async functions
    (function_declaration
      "async"
      name: (identifier) @function.name
      body: (statement_block) @function.body) @function.definition

    (function_expression
      "async"
      name: (identifier)? @function.name
      body: (statement_block) @function.body) @function.definition

    (arrow_function
      "async"
      body: [(expression) (statement_block)] @function.body) @function.definition

    ; Decorators for class methods
    (method_definition
      decorator: (decorator)+ @function.decorator
      name: [(property_identifier) (private_property_identifier)] @function.name
      body: (statement_block) @function.body) @function.definition
    """,

        'class': ("class.definition", "class.name", "class.body", "class.docstring", "class.decorator", """
    ; Class declarations
    (class_declaration
      name: (identifier) @class.name
      body: (class_body) @class.body) @class.definition

    ; Class expressions
    (class
      name: (identifier)? @class.name
      body: (class_body) @class.body) @class.definition

    ; Decorators for classes
    (class_declaration
      decorator: (decorator)+ @class.decorator
      name: (identifier) @class.name
      body: (class_body) @class.body) @class.definition

    (class
      decorator: (decorator)+ @class.decorator
      name: (identifier)? @class.name
      body: (class_body) @class.body) @class.definition
    """)
    },

    "lua": {
        'function': """
    ; Function definitions
    (function_definition
      "function"
      (parameter_list) @function.parameters
      (block) @function.body) @function.definition

    ; Local function definitions
    (local_function_definition_statement
      "local" "function"
      (identifier) @function.name
      (parameter_list) @function.parameters
      (block) @function.body) @function.definition

    ; Function definition statements
    (function_definition_statement
      "function"
      (identifier) @function.name
      (parameter_list) @function.parameters
      (block) @function.body) @function.definition

    ; Function definition statements with table methods
    (function_definition_statement
      "function"
      ((identifier) @function.name
       ":" (identifier) @function.method)
      (parameter_list) @function.parameters
      (block) @function.body) @function.definition
    """,

        'class': ("class.definition", "class.name", "class.body", "class.docstring", "class.decorator", """
    ; Lua doesn't have built-in classes, but tables are often used to simulate them
    ; We'll capture table definitions that might represent "classes"
    (variable_assignment
      (variable_list
        (variable) @class.name)
      "="
      (expression_list
        (table) @class.body)) @class.definition
    """)
    },

    "fortran": {
        'function': """
    (function
      (function_statement
        name: (identifier) @function.name)
      body: (_) @function.body) @function.definition
    """,

        'class': ("class.definition", "class.name", "class.body", "class.docstring", "class.decorator", """
    (derived_type_definition
      (derived_type_statement
        name: (_type_name) @class.name)
      body: (_) @class.body) @class.definition
    """)
    },

    "scala": {
        'function': """
    (function_definition
      (annotation)* @function.decorator
      (modifiers)? @function.decorator
      "def"
      name: (_identifier) @function.name
      type_parameters: (type_parameters)? 
      parameters: (parameters)*
      return_type: ((_type) @function.return_type)?
      body: [
        (indented_block) @function.body
        (block) @function.body
        (expression) @function.body
      ]?) @function.definition

    (function_declaration
      (annotation)* @function.decorator
      (modifiers)? @function.decorator
      "def"
      name: (_identifier) @function.name
      type_parameters: (type_parameters)? 
      parameters: (parameters)*
      return_type: ((_type) @function.return_type)?) @function.definition
    """,

        'class': ("class.definition", "class.name", "class.body", "class.docstring", "class.decorator", """
    (class_definition
      (annotation)* @class.decorator
      (modifiers)? @class.decorator
      "class"
      name: (_identifier) @class.name
      type_parameters: (type_parameters)?
      parameters: (class_parameters)*
      (extends_clause)?
      (derives_clause)?
      body: (template_body)?) @class.definition

    (object_definition
      (annotation)* @class.decorator
      (modifiers)? @class.decorator
      "object"
      name: (_identifier) @class.name
      (extends_clause)?
      (derives_clause)?
      body: (template_body)?) @class.definition

    (trait_definition
      (annotation)* @class.decorator
      (modifiers)? @class.decorator
      "trait"
      name: (_identifier) @class.name
      type_parameters: (type_parameters)?
      parameters: (class_parameters)*
      (extends_clause)?
      (derives_clause)?
      body: (template_body)?) @class.definition

    (enum_definition
      (annotation)* @class.decorator
      "enum"
      name: (_identifier) @class.name
      type_parameters: (type_parameters)?
      parameters: (class_parameters)*
      (extends_clause)?
      (derives_clause)?
      body: (enum_body)) @class.definition
    """)
    },

    "c_sharp": {
        'function': """
    ; Method declarations
    (method_declaration
      (attribute_list)? @function.decorator
      (modifier)* @function.decorator
      type: (_)
      name: (identifier) @function.name
      parameters: (parameter_list)
      body: (block) @function.body) @function.definition

    ; Constructor declarations
    (constructor_declaration
      (attribute_list)? @function.decorator
      (modifier)* @function.decorator
      name: (identifier) @function.name
      parameters: (parameter_list)
      body: (block) @function.body) @function.definition

    ; Destructor declarations
    (destructor_declaration
      (attribute_list)? @function.decorator
      "extern"? @function.decorator
      "~"
      name: (identifier) @function.name
      parameters: (parameter_list)
      body: (block) @function.body) @function.definition

    ; Operator declarations
    (operator_declaration
      (attribute_list)? @function.decorator
      (modifier)* @function.decorator
      type: (_)
      "operator"
      operator: (_)
      parameters: (parameter_list)
      body: (block) @function.body) @function.definition

    ; Conversion operator declarations
    (conversion_operator_declaration
      (attribute_list)? @function.decorator
      (modifier)* @function.decorator
      ("implicit" | "explicit")
      "operator"
      type: (_)
      parameters: (parameter_list)
      body: (block) @function.body) @function.definition

    ; Local function statements
    (local_function_statement
      (attribute_list)? @function.decorator
      (modifier)* @function.decorator
      type: (_)
      name: (identifier) @function.name
      parameters: (parameter_list)
      body: (block) @function.body) @function.definition
    """,

        'class': ("class.definition", "class.name", "class.body", "class.docstring", "class.decorator", """
    ; Class declarations
    (class_declaration
      (attribute_list)? @class.decorator
      (modifier)* @class.decorator
      "class"
      name: (identifier) @class.name
      body: (declaration_list) @class.body) @class.definition

    ; Struct declarations
    (struct_declaration
      (attribute_list)? @class.decorator
      (modifier)* @class.decorator
      "struct"
      name: (identifier) @class.name
      body: (declaration_list) @class.body) @class.definition

    ; Interface declarations
    (interface_declaration
      (attribute_list)? @class.decorator
      (modifier)* @class.decorator
      "interface"
      name: (identifier) @class.name
      body: (declaration_list) @class.body) @class.definition

    ; Enum declarations
    (enum_declaration
      (attribute_list)? @class.decorator
      (modifier)* @class.decorator
      "enum"
      name: (identifier) @class.name
      body: (enum_member_declaration_list) @class.body) @class.definition

    ; Record declarations
    (record_declaration
      (attribute_list)? @class.decorator
      (modifier)* @class.decorator
      "record"
      name: (identifier) @class.name
      body: (declaration_list) @class.body) @class.definition
    """)
    },

    "cobol": {
        'function': """
    (function_definition
      (function_division
        name: (program_name) @function.name)
      (environment_division)?
      (data_division)?
      (procedure_division) @function.body) @function.definition
    """,

        'class': ("class.definition", "class.name", "class.body", "class.docstring", "class.decorator", """
    (data_division
      (file_section
        (file_description
          name: (WORD) @class.name
          (record_description_list) @class.body))) @class.definition

    (data_division
      (working_storage_section
        (data_description
          level_number: (level_number)
          name: (entry_name) @class.name
          (repeat ($._data_description_clause))* @class.body))) @class.definition
    """)
    },

    "matlab": {
        'function': """
    (function_definition
      (function_output)?
      name: (identifier) @function.name
      (function_arguments)?
      (_end_of_line)
      (arguments_statement)*
      body: (block)? @function.body) @function.definition

    (function_definition
      (function_output)?
      "get." @function.decorator
      name: (identifier) @function.name
      (function_arguments)?
      (_end_of_line)
      (arguments_statement)*
      body: (block)? @function.body) @function.definition

    (function_definition
      (function_output)?
      "set." @function.decorator
      name: (identifier) @function.name
      (function_arguments)?
      (_end_of_line)
      (arguments_statement)*
      body: (block)? @function.body) @function.definition
    """,

        'class': ("class.definition", "class.name", "class.body", "class.docstring", "class.decorator", """
    (class_definition
      (attributes)? @class.decorator
      name: (identifier) @class.name
      (superclasses)?
      (_end_of_line)
      body: (_ (properties | methods | events | enumeration | ";")*)+ @class.body) @class.definition
    """)
    }

}
