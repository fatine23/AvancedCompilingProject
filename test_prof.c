struct Book{
   char  title;
   char  author;
   char  subject;
   int   bookId;
};

void printBook( Book book ) {
    print(book.title);
    print(book.author);
    print(book.subject);
    print(book.bookId);
}

int main(int x, int y){
    int id;
    char title = 't';
    char author = 'a';
    char subject = 's';
    id = 100;
    print(id);
    print(title);
    print(author);
    print(subject);
    struct Book myBook;
    return (x + y);
}