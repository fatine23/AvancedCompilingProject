struct Book{
   char  title;
   char  author;
   char  subject;
   int   bookId;
};

int main(int x, int y){
    int id;
    char title;
    char author = 'a';
    char subject = 's';
    id = 100;
    title = 't';
    print(id);
    print(title);
    print(author);
    print(subject);
    struct Book myBook;
    return (x + y);
}