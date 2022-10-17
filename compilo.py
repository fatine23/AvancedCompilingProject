import lark

grammaire = lark.Lark(r"""
exp : SIGNED_NUMBER                     -> exp_nombre
| IDENTIFIER                            -> exp_var
| exp OPBIN exp                         -> exp_opbin
| "(" exp ")"                           -> exp_par

com : IDENTIFIER "=" exp";"             -> assignation
| "if" "(" exp ")" "{" bcom "}"         -> if
| "while" "(" exp ")" "{" bcom "}"      -> while
| "print" "(" exp ")"                   -> print

bcom : (com)*
prg: "main" "("var_list ")"  "{" bcom "return " "(" exp ")" ";" "}"         
var_list :                              -> vide
| IDENTIFIER ("," IDENTIFIER)*          -> aumoinsune

IDENTIFIER : /[a-zA-Z][a-zA-Z0-9]*/

OPBIN : /[+\-*>]/

%import common.WS
%import common.SIGNED_NUMBER
%ignore WS""",
start ="var_list")

ast= grammaire.parse (
"""
main(x, y){
    while (x){
        x=x-1;
        y=y+1;
    }
    return (y);
}
"""
)


def pp_exp(e):
    if e.data in {"exp_nombre", "exp_var"}:
        return e.children[0].value 
    elif e.data == "exp_var":
        return e.children[0].value
    elif e.data == "exp_par":
        return f"({pp_exp(e.children[0].value)})"
    else:
        return f"{pp_exp(e.children[0])} {e.children[1].value} {pp_exp(e.children[2])}"


def vars_exp(e):
    if e.data in "exp_nombre":
        return set()
    elif e.data == "exp_var":
        return e.children[0].value
    elif e.data == "exp_par":
        return vars_exp(e.children[0])
    else:
        L=vars_exp(e.children [0])
        R=vars_exp(e.children [2])
        return  L|R





def asm_exp(e):
    if e.data in "exp_nombre":
        return f"mov rax , {e.children[0].value}\n"
    elif e.data == "exp_var":
        return f"mov rax , [{e.children[0].value}]\n"
    elif e.data == "exp_par":
        return f"({asm_exp(e.children[0])})"
    else:
        E1= asm_exp(e.children [0])
        E2= asm_exp(e.children [2])
        return f""" 
        {E2}
        push rax 
        {E1}
        pop rbx 
        add rax , rbx 
        """






def pp_com(c):
    if c.data == "assignation":
        return f"{c.children[0].value} = {pp_exp(c.children[1])};"
    elif c.data == "if":
        x = f"\n{pp_bcom(c.children[1])}"
        return f"if ({pp_exp(c.children[0])}) {{{x}}}"
    elif c.data == "if_else":
        x = f"\n{pp_bcom(c.children[1])}"
        y = f"\n{pp_bcom(c.children[2])}"
        return f"if ({pp_exp(c.children[0])}) {{{x}}} \nelse {{{y}}}"
    elif c.data == "while":
        return f"while ({pp_exp(c.children[0])}) {{{pp_bcom(c.children[1])}}}"
    elif c.data == "print":
        return f"print({pp_exp(c.children[0])})"

def vars_com(c):
    if c.data == "assignation":
        R=vars_exp(c.children [1])
        return {c.children [0].value }|R
    elif c.data in  {"if", "while "}:
        B=vars_bcom (c.children[1])
        E=vars_exp(c.children[0])
        return E|B
    elif c.data == "print":
        return vars_exp(c.childre[0])


def vars_bcom (bc ):
    S=set()
    for c in bc.children :
        S=S|vars_com(c)
    return S

def asm_com(c):
    if c.data == "assignation":
        E= asm_exp(c.childre  [1])
        return f"""
        {E}
        mov [c.children [0].value], rax
        """
    elif c.data == "if":
        E= asm_exp(c.children[0])
        C= asm_bcom(c.children[1])
        n=next()
        return f"""
        {E}
        cmp rax, 0
        jz fin {n}
        {C}
    fin {n} : nop 
    """
    elif c.data == "while":
        E= asm_exp(c.children[0])
        C= asm_bcom(c.children[1])
        n=next()
        return f"""
        debut{n} : {E}
        cmp rax, 0
        jz fin {n}
        jmp debut{n}
        {C}
    fin {n} : nop 
    """
    elif c.data == "print":
        E= asm_exp(c.children[0])
        return f"""
        {E}
        nmov rdi , fmt 
        mov rsi, rax 
        call printf 
        """
        


def pp_bcom(bc):
    return "\n".join([pp_com(c) for c in bc.children])


def asm_bcom(bc):
    return "".join([asm_com(c) for c in bc.children])


def pp_prg(p):
    L=pp_var_list(p.children[0])
    C=pp_bcom(p.children[1])
    R=pp_exp(p.children[2])
    return "main(%s) {%s return (%s);\n}"%(L,C,R)


def asm_prg(p):
    f=open ("moule.asm")
    moule =f.read()
    C=asm_bcom(p.children[1])
    moule =moule.replace ("BODY", C)
    E=asm_exp(p.children[2])
    moule=moule.replace ("RETURN ", E )
    D="\n".join ([f"{v} : dq 0"for v in vars_prg(p)])
    moule = moule.replace("DECL_VARS ", D )
    s=""
    for i in range (len(p.children [0].children )):
        v=p.children[0].children [i].value 
        e=f"""
        mov rbx , [argv]
        mov rdi ,[rbx+{8*(i+1)}]
        call atoi    #  transforme une chaine de caractere en nombre 
        mov [{v}], rax 
        """
        s=s+e
    moule =moule.replace ("INIT_VARS",s)
    return moule 

    L=pp_var_list(p.children[0])
    
    R=pp_exp(p.children[2])
    return "main(%s) {%s return (%s);\n}"%(L,C,R)

def vars_prg(p):
    print(p.children[0])
    L=set([t.value for t in p.children[0].children])
    C=vars_bcom(p.children[1])
    R=vars_exp(p.children[2])
    return L|C|R



def pp_var_list (vl):
    print(vl)
    return ", ".join ([t.value for t in vl.children ])

ast= grammaire .parse ("""main(x,y,z){
    while(x){
        T=4;
        x=x+3;
    }
    return (y);
}

""")
asm=asm_prg(ast)
f=open ("ouf.asm", "w")
f.write (asm)
f.close()

# print(pp_exp(ast))
print(pp_prg(ast))
#print(pp_bcom(ast))
#print(ast.pretty())