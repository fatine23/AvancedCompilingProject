import lark
from numpy import equal

grammaire = lark.Lark(r"""

exp : SIGNED_INT                 -> exp_int
| SIGNED_FLOAT                   -> exp_float
| "'" CHAR "'"                   -> exp_char
| IDENTIFIER                     -> exp_var
| IDENTIFIER "." IDENTIFIER      -> exp_var_struct
| exp OPBIN exp                  -> exp_opbin
| "(" exp ")"                    -> exp_par
| function_call                  -> exp_function

com : dec                                -> declaration
| IDENTIFIER "=" exp ";"                 -> assignation
| IDENTIFIER "." IDENTIFIER "=" exp ";"  -> assignation_struct_var
| "if" "(" exp ")" "{" bcom "}"          -> if
| "while" "(" exp ")" "{" bcom "}"       -> while
| "print" "(" exp ")" ";"                -> print
| function_call ";"                      -> function_call

function_call : IDENTIFIER "(" exp_list ")"

bdec : (dec)*

bcom : (com)*

dec : TYPE IDENTIFIER ";" -> declaration
| "struct" IDENTIFIER IDENTIFIER ";" -> declaration_struct
| TYPE IDENTIFIER "=" exp ";" -> declaration_expression
| "struct" IDENTIFIER IDENTIFIER "=" exp ";" -> declaration_struct_expression

struct : "struct" IDENTIFIER "{" bdec "}" ";"

function : TYPE IDENTIFIER "(" var_list ")" "{" bcom "return" exp ";" "}"        -> function_return
| "void" IDENTIFIER "(" var_list ")" "{" bcom "}"                                -> function_void
| "struct" IDENTIFIER IDENTIFIER "(" var_list ")" "{" bcom  "return" exp ";" "}" -> function_return_struct

bstruct : (struct)*

bfunction : (function)*

prg : bstruct bfunction "int" "main" "(" var_list ")" "{" bcom "return"  exp ";"  "}" 

exp_list: -> vide
| exp ("," exp)*  -> at_least_one_expression

var_list :                       -> vide
| ((TYPE IDENTIFIER)|(IDENTIFIER IDENTIFIER))("," ((TYPE IDENTIFIER)|(IDENTIFIER IDENTIFIER)))*  -> at_least_one_variable

IDENTIFIER : /[a-zA-Z][a-zA-Z0-9]*/
CHAR : /./
TYPE : "int" | "double" | "float" | "char" | "long"

OPBIN : /[+\-*>]/

%import common.WS
%import common.SIGNED_NUMBER
%import common.SIGNED_INT
%import common.SIGNED_FLOAT
%ignore WS
""",start="prg")

op = {'+' : 'add', '-' : 'sub'}
op_float = {'+' : 'fadd', '-' : 'fsub'} #operations entre deux floats
basic_types = ["int", "char", "double", "float", "long"] 
basic_types_fmt = {"double": "fmtlf", "long": "fmti", "float": "fmtf", "int": "fmti", "char": "fmtc"}#format pour le printf

""" Dictionary to store member's for each declared struct
{
    "struct_name": {
        "member_name" : "member_type",
        ...
    },
    ...
}
"""
structs = {}

""" Dict to store all declared variables in the code
{
    "variable_name" : "variable_type", #variable types includes declared structs
    ...
}
"""
variables = {}

const_count = 0 #number to keep track of the constants found in the code
"""Dict to store the floating point constants found in the code
{
    "const" : "const_index",
    ... 
}
"""
constants = {}

""" Dict to store the parameters of each declared function and its return type
{
    "function_name" : {
        "parameters" :{
            "parameter_name" : "parameter_type",
            ...
        },
        "return": "return_type"
        ...
    },
    ...
}
"""
functions = {}

def verify_var(var_name):
    if var_name not in variables.keys():
        raise Exception(f"error: {var_name} undeclared")

def verify_struct_member(var_name ,member_name):
    if member_name not in structs[variables[var_name]].keys():
        raise Exception(f"error: {member_name} is not a member of {variables[var_name]}")

def get_no_par_expression(exp):
    while exp.data == "exp_par": exp = exp.children[0]
    return exp

def verify_struct_expression(struct_name, exp):
    exp = get_no_par_expression(exp)
    if (exp.data not in ["exp_var", "exp_function"] #other types of expression are not valid to return structs
        or (exp.data == "exp_var" and variables[exp.children[0].value] != struct_name) #variable's return type is wrong
        or (exp.data == "exp_function" and functions[exp.children[0].children[0]]['return'] != struct_name)): #function returns wrong type
        raise Exception(f"error: wrong type of expression, expected struct expression")

def get_struct_var_name_from_expression(exp):
    exp = get_no_par_expression(exp)
    return exp.children[0].value if exp.data == "exp_var" else exp.children[0].children[0].value

def asm_assign_struct(left_variable, right_variable, struct_name):
    asm = ""
    for member, member_type in structs[struct_name].items():
        verify_struct_member(left_variable, member)
        asm += (
    f"""
    mov rax, [{right_variable}.{member}]
    {f'mov [ans{"32" if member_type == "float" else "64"}], rax' if member_type in ["float", "double"] else ""}
    {f'mov rax, [ans{"32" if member_type == "float" else "64"}]' if member_type in ["float", "double"] else ""}
    mov [{left_variable}.{member}], rax
""")
    return asm

def type_exp(e):
    if e.data == "exp_int":
        return ["int", "long"]
    elif e.data == "exp_float":
        return ["float", "double"]
    elif e.data == "exp_char":
        return ["char"]
    elif e.data == "exp_var":
        return [variables[e.children[0].value]]
    elif e.data == "exp_var_struct":
        return [structs[variables[e.children[0].value]][e.children[1].value]]
    elif e.data == "exp_par":
        return type_exp(e.children[0])
    elif e.data == "exp_function":
        return [functions[e.children[0].children[0].value]['return']]
    elif e.data == "exp_opbin":
        types = type_exp(e.children[0]) + type_exp(e.children[2])
        if not set(types).issubset(set(basic_types)):
            raise Exception("error: invalid operand types")
        c_double = types.count("double")
        c_long = types.count("long")
        c_int = types.count("int")
        c_float = types.count("float")
        if c_double or c_float:
            return ["double", "float"]
        elif c_long or c_int:
            return ["long", "int"]
        else:
            return ["char", "int"]

def asm_assign_struct_expression(var_name, expression, struct_name):
    var_type = variables[var_name]
    verify_struct_expression(var_type, expression)
    asm = ""
    if expression.data == "exp_function":
        asm += asm_function_call(expression.children[0])
    right_struct = get_struct_var_name_from_expression(expression)
    asm += asm_assign_struct(var_name, right_struct, var_type)
    return asm 

def asm_function_call(fc):
    function_name = fc.children[0].value
    n_parameters = len(functions[function_name]['parameters'])
    exp_list = fc.children[1].children
    
    if len(exp_list) != n_parameters:
        raise Exception(f"error: wrong number of parameters to call {function_name}")
    
    asm = ""
    for i in range(n_parameters):
        parameter_name = list(functions[function_name]['parameters'].keys())[i]
        parameter_type = list(functions[function_name]['parameters'].values())[i]
        expression = exp_list[i]
        if parameter_type in basic_types:
            asm += asm_assignation(parameter_name, expression)
        else: #struct
            asm += asm_assign_struct_expression(parameter_name, expression, parameter_type)
    asm += f"call {function_name}\n"
    return asm

def asm_exp(e):
    if e.data == "exp_int":
        integer = e.children[0].value
        return f"mov rax, {integer}\n"
    elif e.data == "exp_float":
        constant_index = constants[e.children[0].value]
        return (
    f"""
    mov rax, [const{constant_index}_32]
    mov [ans32], rax
    mov rax, [const{constant_index}_64]
    mov [ans64], rax
""")    
    elif e.data == "exp_char":
        return (f"mov rax, '{e.children[0].value}'\n")
    elif e.data == "exp_var":
        identifier = e.children[0].value 
        verify_var(identifier)
        asm = f"mov rax, [{e.children[0].value}]\n"
        if variables[identifier] == "double":
            asm += f"\tmov [ans64], rax\n"
        if variables[identifier] == "float":
            asm += f"\tmov [ans32], rax\n"
        return asm
    elif e.data == "exp_var_struct":
        identifier = e.children[0].value
        var_struct = e.children[1].value
        verify_var(identifier)
        verify_struct_member(identifier, var_struct) 
        asm = f"\tmov rax, [{identifier}.{var_struct}]\n"
        if structs[variables[identifier]][var_struct] == "double":
            asm += f"mov [ans64], rax\n"
        elif structs[variables[identifier]][var_struct] == "float": 
            asm += f"mov [ans32], rax\n"
        return asm
    elif e.data == "exp_par":
        return asm_exp(e.children[0])
    elif e.data == "exp_function":
        return asm_function_call(e.children[0])
    elif e.data == "exp_opbin":
        types_left = type_exp(e.children[0])
        types_right = type_exp(e.children[2])
        E1 = asm_exp(e.children[0])
        E2 = asm_exp(e.children[2])
        f_in_left = "float" in types_left or "double" in types_left
        f_in_right = "float" in types_right or "double" in types_right
        if f_in_left or f_in_right:
            if f_in_left and f_in_right:
                operator = op_float[e.children[1].value]
                left_word_type = 'dword' if len(types_left) == 1 and types_left[0] == "float" else 'qword'
                left_bit_size = '32' if len(types_left) == 1 and types_left[0] == "float" else '64'
                rigth_word_type = 'dword' if len(types_right) == 1 and types_right[0] == "float" else 'qword'
                rigth_bit_size = '32' if len(types_right) == 1 and types_right[0] == "float" else '64'
                return (
    f"""
    {E1}
    fld {left_word_type} [ans{left_bit_size}]
    {E2}
    {operator} {rigth_word_type} [ans{rigth_bit_size}]
    fst dword [ans32]
    fstp qword [ans64]
""")
            else:
                operator = op_float[e.children[1].value]
                if f_in_left:
                    left_word_type = 'dword' if len(types_left) == 1 and types_left[0] == "float" else 'qword'
                    left_bit_size = '32' if len(types_left) == 1 and types_left[0] == "float" else '64'
                    right_word_type = 'qword' if len(types_right) == 1 and types_right[0] == "long" else 'dword'
                    right_bit_size = '64' if len(types_right) == 1 and types_right[0] == "long" else '32'
                else:
                    left_word_type = 'qword' if len(types_left) == 1 and types_left[0] == "long" else 'dword'
                    left_bit_size = '64' if len(types_left) == 1 and types_left[0] == "long" else '32'
                    right_word_type = 'dword' if len(types_right) == 1 and types_right[0] == "float" else 'qword'
                    right_bit_size = '32' if len(types_right) == 1 and types_right[0] == "float" else '64'
                return (
    f"""
    {E2}
    {'' if f_in_right else f'mov [ans{right_bit_size}], rax'}
    f{'' if f_in_right else 'i' }ld {right_word_type} [ans{right_bit_size}] 
    {E1}
    {'' if f_in_left else f'mov [ans{left_bit_size}], rax'}
    f{'' if f_in_left else 'i' }ld {left_word_type} [ans{left_bit_size}] 
    {operator} st1
    fst dword [ans32]
    fstp qword [ans64]
""")
        else:
            return (
    f"""
    {E2}
    push rax
    {E1}
    pop rbx
    {op[e.children[1].value]} rax, rbx
""")

def pp_exp(e):
    if e.data in ["exp_int", "exp_float", "exp_var"]:
        return e.children[0].value
    elif e.data == "exp_char":
        return f"'{e.children[0].value}'"
    elif e.data == "exp_var_struct":
        return e.children[0].value + '.' + e.children[1].value
    elif e.data == "exp_par":
        return f"({pp_exp(e.children[0])})"
    elif e.data == "exp_function":
        return f"{e.children[0].value}({pp_exp_list(e.children[1])})"
    elif e.data == "exp_opbin":
        return f"{pp_exp(e.children[0])} {e.children[1].value} {pp_exp(e.children[2])}"

def vars_exp(e):
    if e.data == "exp_float":
        global const_count
        constants[e.children[0].value] = const_count
        const_count += 1
    elif e.data == "exp_par":
        vars_exp(e.children[0])
    elif e.data == "exp_opbin":
        vars_exp(e.children[0])
        vars_exp(e.children[2])
    elif e.data == "exp_function":
        vars_exp_list(e.children[0].children[1])

def pp_exp_list(l):
    return ", ".join([pp_exp(exp) for exp in l.children])

def vars_exp_list(el):
    for exp in el.children:
        vars_exp(exp)

cpt = 0
def next():
    global cpt
    cpt += 1
    return cpt

def asm_assignation(var_name, expression):
    var_type = variables[var_name]
    types = type_exp(expression)
    expression = get_no_par_expression(expression)
    if var_type not in basic_types: #struct
        return asm_assign_struct_expression(var_name, expression, var_type)
    asm = asm_exp(expression)
    if "double" in types or "float" in types:
        if var_type not in types:
            raise Exception(f"error: invalid type in assignation")
        asm += f"\tmov rax, [ans{32 if var_type == 'float' else 64}]\n"
    asm += f"\tmov [{var_name}], rax\n"
    return asm

def asm_struct_member_assignation(var_name, member_name, expression):
    struct_name = variables[var_name]
    member_type = structs[struct_name][member_name]
    types = type_exp(expression)
    asm = asm_exp(expression)
    if "double" in types or "float" in types:
        if member_type not in types:
            raise Exception(f"error: invalid type in member assignation")
        asm += f"\tmov rax, [ans{32 if member_type == 'float' else 64}]\n"
    asm += f"\tmov [{var_name}.{member_name}], rax\n"
    return asm

def asm_if_command(exp, bcom):
    E = asm_exp(exp)
    C = asm_bcom(bcom)
    n = next()
    return (
    f"""
    {E}
    cmp rax, 0
    jz fin{n}
    {C}
fin{n} : nop
""")

def asm_while_command(exp, bcom):
    E = asm_exp(exp)
    C = asm_bcom(bcom)
    n = next()
    return f"""
    debut{n} : {E}
    cmp rax, 0
    jz fin{n}
    {C}
    jmp debut{n}
fin{n} : nop
"""

def asm_print_call(exp):
    E = asm_exp(exp)
    types = type_exp(exp)
    fmt = None
    exp_type = None
    if len(types) == 1:
        if types[0] not in basic_types:
            raise Exception(f"error: struct type {types[0]} not allowed here")
        fmt = basic_types_fmt[types[0]]
        exp_type = types[0]
    elif "double" in types:
        fmt = basic_types_fmt["double"]
        exp_type = "double"
    elif "float" in types:
        fmt = basic_types_fmt["float"]
        exp_type = "float"
    elif "int" in types:
        fmt = basic_types_fmt["int"]
        exp_type = "int"
    elif "char" in types:
        fmt = basic_types_fmt["char"]
        exp_type = "char"
    else:
        fmt = basic_types_fmt["long"]    
        exp_type = "long"
    
    if exp_type not in ['double', 'float']:
        return (
    f"""
    {E}
    mov rdi, {fmt}
    mov rsi, rax
    mov rax, 1
    call printf
""")

    elif exp_type == "double":
        return (
    f"""
    {E}
    mov rdi, {fmt}
    movq xmm0, qword [ans64]
    mov rax, 1
    call printf
""")

    else:
        return (
    f"""
    {E}
    mov rdi, {fmt}
    fld	dword [ans32]
    fstp qword [ans64]
    movq xmm0, qword [ans64]
    mov rax, 1
    call printf
""")

def asm_com(c):
    if c.data == "declaration":
        return asm_dec(c.children[0])
    elif c.data == "assignation":
        return asm_assignation(c.children[0].value, c.children[1])
    elif c.data == "assignation_struct_var":
        return asm_struct_member_assignation(c.children[0].value, c.children[1].value, c.children[2])
    elif c.data == "if":
        return asm_if_command(c.children[0], c.children[1])
    elif c.data == "while":
        return asm_while_command(c.children[0], c.children[1]) 
    elif c.data == "print":
        return asm_print_call(c.children[0])
    elif c.data == "function_call":
        return asm_function_call(c.children[0])

def pp_com(c):
    if c.data == "declaration":
        return pp_dec(c.children[0])
    elif c.data == "assignation_struct_var":
        return f"\t{c.children[0].value}.{c.children[1].value} = {pp_exp(c.children[2])};"
    elif c.data == "assignation":
        return f"\t{c.children[0].value} = {pp_exp(c.children[1])};"
    elif c.data == "if":
        x = f"\n{pp_bcom(c.children[1])}"
        return f"\tif ({pp_exp(c.children[0])}) {{{x}}}"
    elif c.data == "while":
        x = f"\n{pp_bcom(c.children[1])}"
        return f"\twhile ({pp_exp(c.children[0])}) {{{x}}}"
    elif c.data == "print":
        return f"\tprint({pp_exp(c.children[0])});"
    elif c.data == "function_call":
        return f"\t{c.children[0].value}({pp_exp_list(c.children[1])});"

def vars_com(c):
    if c.data == "declaration":
        vars_dec(c.children[0])
    elif c.data == "print":
        vars_exp(c.children[0])
    elif c.data == "assignation":
        vars_exp(c.children[1])
    elif c.data == "assignation_struct_var":
        vars_exp(c.children[2])
    elif c.data in {"if", "while"}:
        vars_exp(c.children[0])
        vars_bcom(c.children[1])
    elif c.data == "function_call":
        vars_exp_list(c.children[0].children[1])

def asm_bcom(bc):
    asm = ""
    for command in bc.children:
        asm += asm_com(command)
    return asm

def pp_bcom(bc):
    return "\n".join([pp_com(c) for c in bc.children])

def vars_bcom(bc):
    for c in bc.children:
        vars_com(c)

def pp_var_list(vl):
    S=[]
    for t in range (len(vl.children)//2):
        S.append(vl.children[2*t].value + " " + vl.children[(2*t)+1].value)
    return ", ".join([t for t in S])

def vars_var_list(vl):
    for t in range(len(vl.children)//2):
        variables[vl.children[(2*t)+1].value] = vl.children[(2*t)].value 

def pp_struct(s):
    Y=s.children[0]
    L=pp_bdec(s.children[1])
    return "struct %s {\n%s \n };" % (Y,L)

def vars_struct(s):
    structs[s.children[0].value] = {}
    for dec in s.children[1].children:
        if dec.data in ["declaration", "declaration_struct"]:
            structs[s.children[0].value][dec.children[1].value] = dec.children[0].value
        else:
            raise Exception("Assignations are not allowed in structs definitions")

def pp_bstruct(bs):
    return "\n".join([pp_struct(d) for d in bs.children])

def vars_bstruct(bs):
    for s in bs.children:
        vars_struct(s)

def pp_dec(d):
    if d.data == "declaration":
        return f"\t{(d.children[0])} {(d.children[1])};"
    elif d.data == "declaration_struct":
        return f"\tstruct {d.children[0]} {d.children[1]};"
    elif d.data == "declaration_expression":
        return f"\t{d.children[0]} {d.children[1]} = {pp_exp(d.children[2])};"
    elif d.data == "declaration_struct_expression":
        return f"\tstruct {d.children[0]} {d.children[1]} = {pp_exp(d.children[2])};"

def vars_dec(d):
    variables[d.children[1].value] = d.children[0].value
    if d.data in ["declaration_expression", "declaration_struct_expression"]:
        vars_exp(d.children[2])

def asm_dec(d):
    if d.data not in ["declaration_expression", "declaration_struct_expression"]:
        return ""
    var_name = d.children[1].value
    var_type = d.children[0].value
    exp = d.children[2]
    verify_var(var_name)
    return asm_assignation(var_name, exp)

def pp_bdec(bdec):
    return "\n".join([pp_dec(d) for d in bdec.children])

def vars_bdec(bdec):
    S = set()
    for dec in bdec.children:
        S = S | vars_dec(dec)
    return S

def pp_function(f):
    if f.data == "function_void":
        name = f.children[0]
        var_list = pp_var_list(f.children[1])
        command_block = pp_bcom(f.children[2])
        return "void %s(%s){\n%s\n}" % (name, var_list, command_block)
        
    elif f.data in ["function_return", "function_return_struct"]:
        A=f.children[0]
        B=f.children[1]
        C=pp_var_list(f.children[2])
        D=pp_bcom(f.children[3])
        E=pp_exp(f.children[4])
        return f"{'struct' if f.data == 'function_return_struct' else ''} {A} {B}({C}){{{D}\n\treturn({E});\n}}"

def asm_function(f):
    if f.data == "function_void":
        name = f.children[0]
        command_block=asm_bcom(f.children[2])
        s=f"""
{name}:
    push rbp
    mov rbp,rsp
    """  
        s=s+f"""
        {command_block}
        leave
        ret
"""
        return s
    elif f.data =="function_return":
        TYPE =f.children[0]
        name=f.children[1]
        command_block=asm_bcom(f.children[3])
        EXP=asm_exp(f.children[4])
        s=f"""
{name}:
    push rbp
    mov rbp,rsp
    {command_block}
    """
        s=s+EXP
        s=s+f"""
    leave
    ret
"""
        return(s)
    elif f.data == "function_return_struct":
        struct_name = f.children[0].value
        function_name = f.children[1]
        bcom = asm_bcom(f.children[3])
        exp = f.children[4]
        verify_struct_expression(struct_name, exp)
        asm_return = ""
        if exp.data == "exp_var":
            asm_return = asm_assign_struct(function_name, exp.children[0].value, struct_name)
        elif exp.data == "exp_function":
            asm_return = asm_assign_struct(function_name, exp.children[0].children[0], struct_name) 
        return (
    f"""
{function_name}:
    push rbp
    mov rbp,rsp
    {bcom}
    {asm_return}
    leave
    ret
""")
        
def vars_function(f):
    name = f.children[0].value if f.data == "function_void" else f.children[1].value
    var_list = f.children[1] if f.data == "function_void" else f.children[2]
    return_type = "void" if f.data == "function_void" else f.children[0].value

    if f.data == "function_return_struct":
        variables[name] = return_type

    functions[name] = {'parameters': {}}
    for t in range(len(var_list.children)//2):
        functions[name]['parameters'][var_list.children[(2*t)+1].value] = var_list.children[(2*t)].value
    functions[name]['return'] = return_type
    vars_bcom(f.children[2 if f.data == "function_void" else 3])
    vars_var_list(var_list)
    if f.data in ["function_return", "function_return_struct"]:
        vars_exp(f.children[4])

def pp_bfunction(bf):
    return "\n".join([pp_function(d) for d in bf.children])

def asm_bfunction(bf):
    asm = ""
    for function in bf.children:
        asm += asm_function(function)
    return asm

def vars_bfunction(bf):
    for f in bf.children:
        vars_function(f)

def pp_prg(p):
    print(pp_bstruct(p.children[0])) #bstruct
    print(pp_bfunction(p.children[1])) #bfunction
    print(f"int main ({pp_var_list(p.children[2])}){{") #main arguments (var_list)
    print(pp_bcom(p.children[3])) #main body (bcom)
    print(f"\treturn({pp_exp(p.children[4])});\n}}") #return exp

def vars_prg(p):
    vars_bstruct(p.children[0])
    vars_bfunction(p.children[1])
    vars_var_list(p.children[2])
    vars_bcom(p.children[3])
    vars_exp(p.children[4])

def asm_decl_basic_var(variable, variable_type):
    if variable_type == "char":
        return f"{variable} :resb 1 \n"
    elif variable_type in ["int", "float"]:
        return f"{variable} : resd 1 \n"
    elif variable_type in ["double", "long"]:
        return f"{variable} : resq 1 \n"

def asm_decl_struct_var(variable, member_name, member_type):
    if member_type == "char":
        return f"{variable}.{member_name} : resb 1 \n"
    elif member_type in ["int", "float"]:
        return f"{variable}.{member_name} : resd 1 \n"
    elif member_type in ["double", "long"]:
        return f"{variable}.{member_name} : resq 1 \n"

def asm_decl_vars():
    asm = ""
    for var, var_type in variables.items():
        if var_type in basic_types: #int, float, double, etc...
            asm += asm_decl_basic_var(var, var_type)
        else: #struct
            if var_type not in structs.keys():
                raise Exception(f"{var_type} type is not defined")
            for member, member_type in structs[var_type].items():
                asm += asm_decl_struct_var(var, member, member_type)
    return asm

def asm_decl_const():
    asm = ""
    for const, index in constants.items():
        asm += f"const{index}_32: dd {const}\n"
        asm += f"const{index}_64: dq {const}\n"
    return asm

def asm_prg(p):
    f = open("template.asm")
    moule = f.read()
    vars_prg(p)
    #structs_asm = asm_bstruct(p.children[0])# rien a faire

    C = asm_bcom(p.children[3])
    moule = moule.replace("BODY", C)
    E = asm_exp(p.children[4])
    moule = moule.replace("RETURN", E)
    F = asm_bfunction(p.children[1])
    moule = moule.replace("FUNCTIONS", F)
    #D = "\n".join([f"{v} : dq 0" for v in variables.keys()])
    D = asm_decl_vars()
    moule = moule.replace("DECL_VARS", D)
    constants_asm = asm_decl_const()
    moule = moule.replace("DECL_CONSTS", constants_asm) 
    s = ""
    for i in range(len(p.children[2].children)//2):
        v = p.children[2].children[2*i+1].value
        e = f"""
        mov rbx, [argv]
        mov rdi, [rbx + { 8*(i+1)}]
        xor rax, rax
        call atoi
        mov [{v}], rax
"""
        s = s + e
    moule = moule.replace("INIT_VARS", s)    
    return moule

f_test = open("test_prof.c")
test = f_test.read()
ast = grammaire.parse(test)
asm = asm_prg(ast)
#print(f"Constants: {constants}\n")
#print(f"Variables: {variables}\n")
#print(f"Structs: {structs}\n")
#print(f"Functions: {functions}\n")
f = open("ouf.asm", "w")
f.write(asm)
f.close()

