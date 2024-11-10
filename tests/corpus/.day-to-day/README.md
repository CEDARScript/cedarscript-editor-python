
UPDATE FUNCTION "my_func"                                                                                                                                              
FROM FILE "1.py"                                                                                                                      
REPLACE WHOLE WITH CASE                                                                                                                                                 
WHEN REGEX r'''# Some comment''' THEN SUB                                                                                                        
r'''# Some comment\n.*?something = find\[search\["col1"\]\.isna\(\)\]'''                                                  
r'''# Some comment (and then some)                                                                                          
elements_type_2 = search[search["something"].isna()]                                                                                            
elements_type_1 = elements_type_2[elements_type_2["req"].isna()]'''                                                           
END;                                      

instead,:

UPDATE FUNCTION "my_func"                                                                                                                                              
FROM FILE "1.py"                                                                                                                      
REPLACE LINE REGEX r'''# Some comment''' WITH CONTENTS '''
# Some comment (and then some)                                                                                          
elements_type_2 = search[search["something"].isna()]                                                                                            
elements_type_1 = elements_type_2[elements_type_2["req"].isna()]'''                                                           
''';
