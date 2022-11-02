extern printf
extern  atoi 
section .data 
fmt :db "%d", 10 ,0
argc :dq 0
argv : dq 0
book.title : db 0 
book.author : db 0 
book.subject : db 0 
book.bookId : dd 0 
x : dd 0 
y : dd 0 
id : dd 0 
title : db 0 
author : db 0 
subject : db 0 
myBook.title : db 0 
myBook.author : db 0 
myBook.subject : db 0 
myBook.bookId : dd 0 


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
         
    
        mov rax, 't'
        mov [title], rax
        
        mov rax, 'a'
        mov [author], rax
        
        mov rax, 's'
        mov [subject], rax
        
        mov rax, 100

        mov [id], rax        
        
        mov rax, [id]

        mov rdi, fmt
        mov rsi, rax
        call printf
        
        mov rax, [title]

        mov rdi, fmt
        mov rsi, rax
        call printf
        
        mov rax, [author]

        mov rdi, fmt
        mov rsi, rax
        call printf
        
        mov rax, [subject]

        mov rdi, fmt
        mov rsi, rax
        call printf
         
    
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