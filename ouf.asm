extern printf
extern  atoi 
section .data 
fmt :db "%d", 10 ,0
argc :dq 0
argv : dq 0
x : dd 0 
y : dd 0 
i : dd 0 
c : db 0 


section .text
global main 
main : 
    push rbp
    mov [argc], rdi 
    mov [argv ], rsi
    
        mov rbx, [argv]
        mov rdi, [rbx + 8]
        xor rax, rax
        call atoi
        mov [x], rax
        
        mov rbx, [argv]
        mov rdi, [rbx + 16]
        xor rax, rax
        call atoi
        mov [y], rax
         
    
        mov rax, '$'
        mov [c], rax
        
        mov rax, [i]

        mov rdi, fmt
        mov rsi, rax
        call printf
        
        mov rax, 100

        mov [i], rax        
         
    
        mov rax, [y]

        push rax
        mov rax, [x]

        pop rbx
        add rax, rbx
         
    mov rdi , fmt 
    mov rsi , rax
    call printf 
    pop rbp 
    ret 