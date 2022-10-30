import lark
from numpy import equal

grammaire = lark.Lark(r"""

exp : SIGNED_NUMBER              -> exp_nombre
| IDENTIFIER                     -> exp_var
| IDENTIFIER "." IDENTIFIER      -> exp_var_struct
| exp OPBIN exp                  -> exp_opbin
| "(" exp ")"                    -> exp_par
| IDENTIFIER "(" var_list ")"    -> exp_function

com : dec                        -> declaration
| IDENTIFIER "=" exp ";"         -> assignation
| IDENTIFIER "." IDENTIFIER "=" exp ";" -> assignation_struct_var
| "if" "(" exp ")" "{" bcom "}"  -> if
| "while" "(" exp ")" "{" bcom "}"  -> while
| "print" "(" exp ")" ";"              -> print
| "printf" "(" exp ")" ";"             -> printf
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

TYPE : "int" | "double" | "float" | "bool" | "char" | "long"

OPBIN : /[+\-*>]/

%import common.WS
%import common.SIGNED_NUMBER
%ignore WS
""",start="prg")

op = {'+' : 'add', '-' : 'sub'}

def asm_exp(e):
    if e.data == "exp_nombre":
        return f"mov rax, {e.children[0].value}\n"
    elif e.data == "exp_var":
        return f"mov rax, [{e.children[0].value}]\n"
    elif e.data == "exp_par":
        return asm_exp(e.children[0])
    else:
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
    if e.data in {"exp_nombre", "exp_var"}:
        return e.children[0].value
    elif e.data == "exp_var_struct":
        return e.children[0].value + '.' + e.children[1].value
    elif e.data == "exp_par":
        return f"({pp_exp(e.children[0])})"
    else:
        return f"{pp_exp(e.children[0])} {e.children[1].value} {pp_exp(e.children[2])}"

def pp_exp_list(l):
    return ", ".join([pp_exp(exp) for exp in l.children])

def vars_exp(e):
    if e.data  == "exp_nombre":
        return set()
    elif e.data ==  "exp_var":
        return { e.children[0].value }
    elif e.data == "exp_par":
        return vars_exp(e.children[0])
    else:
        L = vars_exp(e.children[0])
        R = vars_exp(e.children[2])
        return L | R

cpt = 0
def next():
    global cpt
    cpt += 1
    return cpt

def asm_com(c):
    if c.data == "assignation":
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
        return f"{c.children[0]}.{c.children[1]} = {pp_exp(c.children[2])};"
    elif c.data == "assignation":
        return f"{c.children[0].value} = {pp_exp(c.children[1])};"
    elif c.data == "if":
        x = f"\n{pp_bcom(c.children[1])}"
        return f"if ({pp_exp(c.children[0])}) {{{x}}}"
    elif c.data == "while":
        x = f"\n{pp_bcom(c.children[1])}"
        return f"while ({pp_exp(c.children[0])}) {{{x}}}"
    elif c.data == "print":
        return f"print({pp_exp(c.children[0])});"
    elif c.data == "function_call":
        return f"{c.children[0]}({pp_exp_list(c.children[1])});"


def vars_com(c):
    if c.data == "assignation":
        R = vars_exp(c.children[1])
        return {c.children[0].value} | R
    elif c.data in {"if", "while"}:
        B = vars_bcom(c.children[1])
        E = vars_exp(c.children[0]) 
        return E | B
    elif c.data == "print":
        return vars_exp(c.children[0])

def asm_bcom(bc):
    return "".join([asm_com(c) for c in bc.children])

def pp_bcom(bc):
    return "\n".join([pp_com(c) for c in bc.children])

def vars_bcom(bc):
    S = set()
    for c in bc.children:
        S = S | vars_com(c)
    return S

def pp_var_list(vl):
    S=[]
    for t in range (len(vl.children)//2):
        S.append(vl.children[2*t].value + " " + vl.children[(2*t)+1].value)
    return ", ".join([t for t in S])

def asm_prg(p):
    f = open("moule.asm")
    moule = f.read()
    C = asm_bcom(p.children[1])
    moule = moule.replace("BODY", C)
    E = asm_exp(p.children[2])
    moule = moule.replace("RETURN", E)
    D = "\n".join([f"{v} : dq 0" for v in vars_prg(p)])
    moule = moule.replace("DECL_VARS", D)
    s = ""
    for i in range(len(p.children[0].children)):
        v = p.children[0].children[i].value
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

def vars_prg(p):
    L = set([t.value for t in p.children[0].children])
    C = vars_bcom(p.children[1])
    R = vars_exp(p.children[2])
    return L | C | R

def pp_struct(s):
    Y=s.children[0]
    L=pp_bdec(s.children[1])
    return "struct %s {\n%s \n };" % (Y,L)

def pp_bstruct(bs):
    return "\n".join([pp_struct(d) for d in bs.children])


def pp_dec(d):
    if d.data == "declaration":
        return f"{(d.children[0])} {(d.children[1])};"
    elif d.data == "declaration_struct":
        return f"struct {d.children[0]} {d.children[1]};"
    elif d.data == "declaration_expression":
        return f"{d.children[0]} {d.children[1]} = {pp_exp(d.children[2])};"
    elif d.data == "declaration_struct_expression":
        return f"struct {d.children[0]} {d.children[1]} = {pp_exp(d.children[2])};"

def pp_bdec(bdec):
    return "\n".join([pp_dec(d) for d in bdec.children])

def pp_function(f):
    if f.data == "function_void":
        name = f.children[0]
        var_list = pp_var_list(f.children[1])
        command_block = pp_bcom(f.children[2])
        return "void %s ( %s ) {\n %s \n}" % (name, var_list, command_block)
        
    elif f.data =="function_return":
        A=f.children[0]
        B=f.children[1]
        C=pp_var_list(f.children[2])
        D=pp_bcom(f.children[3])
        E=pp_var_list(f.children[4])
        return "%s %s ( %s ) {\n%s \nreturn %s;\n}" % (A, B, C,D,E)
    
def pp_bfunction(bf):
    return "\n".join([pp_function(d) for d in bf.children])

def pp_prg(p):
    print(pp_bstruct(p.children[0])) #bstruct
    print(pp_bfunction(p.children[1])) #bfunction
    print(f"int main ({pp_var_list(p.children[2])}){{") #main arguments (var_list)
    print(pp_bcom(p.children[3])) #main body (bcom)
    print(f"return({pp_exp(p.children[4])});\n}}") #return exp
    

ast = grammaire.parse("""
struct Books {
   char  title;
   char  author;
   char  subject;
   int   bookId;
};

void printBook( Books book ) {
    print(book.title);
    print(book.author);
    print(book.subject);
    print(book.bookId);
}

int main(int A,int B ) {

   struct Books Book1;        
   struct Books Book2;        
   Book1.bookId = 6495407;
   Book2.bookId = 6495700;
 
   printBook( Book1 );

   printBook( Book2 );

   return (0);
}
""")
pp_prg(ast)
#print(asm)
#f = open("ouf.asm", "w")
#f.write(asm)
#f.close()

