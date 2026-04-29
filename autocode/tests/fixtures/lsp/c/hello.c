#include "hello.h"

int local_add(int left, int right) {
    return left + right;
}

struct LocalBox make_box(int value) {
    struct LocalBox box = { .value = value };
    return box;
}

int main(void) {
    struct LocalBox box = make_box(local_add(1, 2));
    return box.value;
}

int broken(void) {
    return missing_local_symbol;
}
