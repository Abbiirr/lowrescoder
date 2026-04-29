#pragma once

struct LocalBox {
    int value;
};

int local_add(int left, int right);
struct LocalBox make_box(int value);
