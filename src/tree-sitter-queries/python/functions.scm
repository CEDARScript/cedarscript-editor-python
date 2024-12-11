; Function Definitions
(function_definition
    {definition_base}
    {common_body}
) @function.definition

; Decorated Function Definitions
(decorated_definition
    (decorator)+ @function.decorator
    (function_definition
        {definition_base}
        {common_body}
    ) @function.definition
)
