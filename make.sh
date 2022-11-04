python3 compilo.py
nasm -f elf64 ouf.asm
gcc -no-pie -fno-pie ouf.o
./a.out 10 15 7