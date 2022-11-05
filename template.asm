extern printf
extern  atoi 
global main 
section .data 

fmti : db "%i", 10, 0
fmtli : db "%li", 10, 0
fmtlf : db "%lf", 10, 0
fmtf : db "%f", 10, 0
fmtc : db "%c", 10, 0
argc : dq 0
argv : dq 0
DECL_CONSTS

section .bss
ans32 : resd 1
ans64 : resq 1

DECL_VARS


section .text

FUNCTIONS

main : 
    push rbp
    mov [argc], rdi 
    mov [argv ], rsi
    INIT_VARS 
    BODY 
    RETURN 
    mov rdi , fmti 
    mov rsi , rax
    call printf 
    pop rbp 
    ret 