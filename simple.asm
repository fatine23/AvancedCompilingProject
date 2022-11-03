extern printf
section .data 
hello : db"helle world %d" ,10, 0
fmt :db "%s" , 10, 0
argc :dq 0
argv : dq 0


section .text
global main 
main: 
    push rbp
    mov[argc], rdi
    mov[argv], rsi
    mov rdi , hello 
    mov rsi , [argc] ; "rsi=42"
    call printf 
    mov rdi , fmt 
    mov rbx , [argv]
    mov rdi , [rbx+8]
    call atoi 
    mov rdi , hello 
    mov rsi , rax
    call printf 
    pop rbp 
    ret

    