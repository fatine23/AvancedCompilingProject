extern printf 
section data 
fmt :db "%d", 10 ,0
argc :dq 0
argv : dq 0
y : dq 0
x : dq 0

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
         
    
        debut1 : mov rax, [x]

        cmp rax, 0
        jz fin1
        
        
        mov rax, 1

        push rax
        mov rax, [x]

        pop rbx
        sub rax, rbx
        
        mov [x], rax        
        
        
        mov rax, 1

        push rax
        mov rax, [y]

        pop rbx
        add rax, rbx
        
        mov [y], rax        
        
        jmp debut1
fin1 : nop
 
    mov rax, [y]
 
    mov rdi , fmt 
    mov rsi , rax
    call printf 
    pop rbp 
    ret 