struct Book{
   char  title;
   char  author;
   char  subject;
   int   bookId;
};

int blabla(int a,int b){
    return(a+b);
}

int main(int x, int y,int z){
    int id;
    char title;
    char author = 'a';
    char subject = 's';
    int u;
    id = 100;
    title = 't';
    print(id);
    print(title);
    print(author);
    print(subject);
    struct Book myBook;
    print(y);
    x=blabla(x,y);
    print(x);
    print(y);
    print(z);
    return (x+y+z);
}