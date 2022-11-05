struct Book{
    int   bookId;
    char  title;
    float rating;
    double critRating;
    long  profit;
};

void printBook( Book book ) {
    print(book.bookId);
    print(book.title);
    print(book.rating);
    print(book.critRating);
    print(book.profit);
}

double get2(){
    return 2.0;
}

int get5(){
    return 5;
}

int main() {
    struct Book book1;        
    struct Book book2;        

    book1.bookId = 15; 
    book2.bookId = 20;
    int i = book1.bookId + book2.bookId; 
    print(i);

    char c = 'a';
    book2.title = c + 3;
    book1.title = 't' - 4;
    print(book1.title);
    print(book2.title);

    float f = 4.8;
    book1.rating = f;
    book1.critRating = f - 0.05;
    book2.critRating = book1.critRating;
    book2.rating = 3.8;
    print(book1.rating);
    print(book1.critRating);
    print(book2.rating);
    print(book2.critRating);

    long l = i + 12345667;
    book1.profit = l - book1.bookId;
    book2.profit = book1.profit - 100000;
    print(l);
    print(book1.profit);
    print(book2.profit);


    printBook(book1);
    book1 = book2;
    printBook(book1);

    print(get2());
    print(get5());
    return (0);
}