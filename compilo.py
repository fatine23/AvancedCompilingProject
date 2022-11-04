import lark
from numpy import equal

grammaire = lark.Lark(r"""

exp : SIGNED_NUMBER              -> exp_nombre
| "'" CHAR "'"                   -> exp_char
| IDENTIFIER                     -> exp_var
| IDENTIFIER "." IDENTIFIER      -> exp_var_struct
| exp OPBIN exp                  -> exp_opbin
| "(" exp ")"                    -> exp_par
| IDENTIFIER "(" exp_list ")"    -> exp_function

com : dec                        -> declaration
| IDENTIFIER "=" exp ";"         -> assignation
| IDENTIFIER "." IDENTIFIER "=" exp ";" -> assignation_struct_var
| "if" "(" exp ")" "{" bcom "}"  -> if
| "while" "(" exp ")" "{" bcom "}"  -> while
| "print" "(" exp ")" ";"              -> print
| IDENTIFIER "(" exp_list ")" ";"      -> function_call

bdec : (dec)*

bcom : (com)*

dec : TYPE IDENTIFIER ";" -> declaration
| "struct" IDENTIFIER IDENTIFIER ";" -> declaration_struct
| TYPE IDENTIFIER "=" exp ";" -> declaration_expression
| "struct" IDENTIFIER IDENTIFIER "=" exp ";" -> declaration_struct_expression

struct : "struct" IDENTIFIER "{" bdec "}" ";"

function : TYPE IDENTIFIER "(" var_list ")" "{" bcom "return" exp ";" "}" -> function_return
| "void" IDENTIFIER "(" var_list ")" "{" bcom "}"  -> function_void

bstruct : (struct)*

bfunction : (function)*

prg : bstruct bfunction "int" "main" "(" var_list ")" "{" bcom "return" "(" exp ")" ";"  "}" 

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
%ignore WS
""",start="prg")

op = {'+' : 'add', '-' : 'sub'}

basic_types = ["int", "char", "double", "float", "long"]

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

def asm_assign_struct(left_struct, right_struct, struct_name):
    asm = ""
    for member in structs[struct_name].keys():
        asm += f"""
        mov rax, [{left_struct}.{member}]
        mov [{right_struct}.{member}], rax
        """
    return asm

def asm_exp(e):
    if e.data == "exp_nombre":
        number = e.children[0].value
        return f"mov rax, {number}\n"
    elif e.data == "exp_char":
        return f"mov rax, '{e.children[0].value}'"
    elif e.data == "exp_var":
        identifier = e.children[0].value 
        verify_var(identifier)
        return f"mov rax, [{e.children[0].value}]\n"
    elif e.data == "exp_var_struct":
        identifier = e.children[0].value
        var_struct = e.children[1].value
        verify_var(identifier)
        verify_struct_member(identifier, var_struct) 
        return f"mov rax, [{identifier}.{var_struct}]\n"
    elif e.data == "exp_par":
        return asm_exp(e.children[0])
    elif e.data == "exp_function":
        function_name = e.children[0].value
        n_parameters = len(functions[function_name]['parameters'])
        exp_list = e.children[1].children
        if len(exp_list) != n_parameters:
            raise Exception(f"error: wrong number of parameters to call {function_name}")
        
        asm = ""
        for i in range(n_parameters):
            E = asm_exp(exp_list[i])
            asm += f"""
            {E}
            mov [{list(functions[function_name]['parameters'].keys())[i]}], rax
            """
        asm += f"call {function_name}"
        return asm
    elif e.data == "exp_opbin":
        E1 = asm_exp(e.children[0])
        E2 = asm_exp(e.children[2])
        return f"""
        {E2}
        push rax
        {E1}
        pop rbx
        {op[e.children[1].value]} rax, rbx
        """

def pp_exp(e):
    if e.data in ["exp_nombre", "exp_var"]:
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

def pp_exp_list(l):
    return ", ".join([pp_exp(exp) for exp in l.children])

cpt = 0
def next():
    global cpt
    cpt += 1
    return cpt

def asm_com(c):
    if c.data == "declaration":
        return asm_dec(c.children[0])
    elif c.data == "assignation":
        E = asm_exp(c.children[1])
        return f"""
        {E}
        mov [{c.children[0].value}], rax        
        """
    elif c.data == "if":
        E = asm_exp(c.children[0])
        C = asm_bcom(c.children[1])
        n = next()
        return f"""
        {E}
        cmp rax, 0
        jz fin{n}
        {C}
fin{n} : nop
"""
    elif c.data == "while":
        E = asm_exp(c.children[0])
        C = asm_bcom(c.children[1])
        n = next()
        return f"""
        debut{n} : {E}
        cmp rax, 0
        jz fin{n}
        {C}
        jmp debut{n}
fin{n} : nop
"""
    elif c.data == "print":
        E = asm_exp(c.children[0])
        return f"""
        {E}
        mov rdi, fmt
        mov rsi, rax
        call printf
        """

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
    elif c.data in {"if", "while"}:
        B = vars_bcom(c.children[1])

def asm_bcom(bc):
    return "".join([asm_com(c) for c in bc.children])

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

def asm_dec(d):
    if d.data == "declaration_expression":
        var_name = d.children[1].value
        verify_var(var_name)
        var_type = d.children[0].value
        exp = asm_exp(d.children[2])
        return f"""
        {exp}
        mov [{var_name}], rax
        """
    elif d.data == "declaration_struct_expression":
        verify_struct_member(var_name, var_type)
        left_struct = var_name
        struct_name = var_type
        right_struct = d.children[2].children[0].value
        type_of_expresion = d.children[2].data
        if type_of_expresion != "exp_var" or variables[right_struct] != struct_name:
            raise Exception(f"invalid expression to assign to {left_struct}")
        return asm_assign_struct(left_struct, right_struct, struct_name)
    else: #no assembly needed
        return ""

def pp_bdec(bdec):
    return "\n".join([pp_dec(d) for d in bdec.children])

def vars_bdec(bdec):
    S = set()
    for dec in bdec.children:
        S = S | vars_dec(dec)
    return S

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
        pop rbp
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
    pop rbp
    ret
            """
        return(s)

        

def pp_function(f):
    if f.data == "function_void":
        name = f.children[0]
        var_list = pp_var_list(f.children[1])
        command_block = pp_bcom(f.children[2])
        return "void %s(%s){\n%s\n}" % (name, var_list, command_block)
        
    elif f.data =="function_return":
        A=f.children[0]
        B=f.children[1]
        C=pp_var_list(f.children[2])
        D=pp_bcom(f.children[3])
        E=pp_exp(f.children[4])
        return "%s %s(%s){%s\n\treturn(%s);\n}" % (A, B, C,D,E)

def vars_function(f):
    name = f.children[0].value if f.data == "function_void" else f.children[1].value
    var_list = f.children[1] if f.data == "function_void" else f.children[2]
    return_type = "void" if f.data == "function_void" else f.children[0].value

    functions[name] = {'parameters': {}}
    for t in range(len(var_list.children)//2):
        functions[name]['parameters'][var_list.children[(2*t)+1].value] = var_list.children[(2*t)].value
    functions[name]['return'] = return_type
    
    vars_var_list(var_list)

def pp_bfunction(bf):
    return "\n".join([pp_function(d) for d in bf.children])

def asm_bfunction(bf):
    return "\n".join([asm_function(d) for d in bf.children])

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

def asm_decl_basic_var(variable, variable_type):
    if variable_type == "char":
        return f"{variable} : db 0 \n"
    elif variable_type in ["int", "float"]:
        return f"{variable} : dd 0 \n"
    elif variable_type in ["double", "long"]:
        return f"{variable} : dq 0 \n"

def asm_decl_struct_var(variable, member_name, member_type):
    if member_type == "char":
        return f"{variable}.{member_name} : db 0 \n"
    elif member_type in ["int", "float"]:
        return f"{variable}.{member_name} : dd 0 \n"
    elif member_type in ["double", "long"]:
        return f"{variable}.{member_name} : dq 0 \n"

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

def asm_prg(p):
    f = open("template.asm")
    moule = f.read()
    vars_prg(p)
    #structs_asm = asm_bstruct(p.children[0])# rien a faire
    #functions_asm = asm_bfunction(p.children[1])

    C = asm_bcom(p.children[3])
    moule = moule.replace("BODY", C)
    E = asm_exp(p.children[4])
    moule = moule.replace("RETURN", E)
    F = asm_bfunction(p.children[1]) #TO DO asm_bfunction
    moule = moule.replace("FUNCTIONS", F)
    #D = "\n".join([f"{v} : dq 0" for v in variables.keys()])
    D = asm_decl_vars()
    moule = moule.replace("DECL_VARS", D)
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
#print(f"Variables: {variables}\n")
#print(f"Structs: {structs}\n")
#print(f"Functions: {functions}\n")
f = open("ouf.asm", "w")
f.write(asm)
f.close()