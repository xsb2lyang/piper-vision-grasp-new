#include <linux/can.h>
#include <linux/can/raw.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

// gcc -shared -fPIC can_send.c -o libcan_send.so

/// 打开 CAN 设备，返回 socket fd，失败返回 -1
int open_can(const char* name) {
    int sock = socket(PF_CAN, SOCK_RAW, CAN_RAW);
    if (sock < 0) {
        perror("socket(PF_CAN)");
        return -1;
    }

    struct ifreq ifr;
    memset(&ifr, 0, sizeof(ifr));
    strncpy(ifr.ifr_name, name, IFNAMSIZ - 1);

    if (ioctl(sock, SIOCGIFINDEX, &ifr) < 0) {
        perror("SIOCGIFINDEX");
        close(sock);
        return -1;
    }

    struct sockaddr_can addr;
    memset(&addr, 0, sizeof(addr));
    addr.can_family = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;

    if (bind(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind(can)");
        close(sock);
        return -1;
    }

    return sock;
}

int get_can_name(int fd, char* out_name, int out_size) {
    struct sockaddr_can addr;
    socklen_t len = sizeof(addr);

    if (getsockname(fd, (struct sockaddr *)&addr, &len) < 0) {
        perror("getsockname");
        return -1;
    }

    struct ifreq ifr;
    memset(&ifr, 0, sizeof(ifr));
    ifr.ifr_ifindex = addr.can_ifindex;

    if (ioctl(fd, SIOCGIFNAME, &ifr) < 0) {
        perror("SIOCGIFNAME");
        return -1;
    }

    strncpy(out_name, ifr.ifr_name, out_size - 1);
    out_name[out_size - 1] = '\0';
    return 0;
}

/// 发送 8 字节 CAN 数据帧
bool send_int_data(int sock, int id,
                   uint8_t d0, uint8_t d1, uint8_t d2, uint8_t d3,
                   uint8_t d4, uint8_t d5, uint8_t d6, uint8_t d7) 
{
    struct can_frame frame;
    memset(&frame, 0, sizeof(frame));

    frame.can_id  = id;
    frame.can_dlc = 8;

    frame.data[0] = d0;
    frame.data[1] = d1;
    frame.data[2] = d2;
    frame.data[3] = d3;
    frame.data[4] = d4;
    frame.data[5] = d5;
    frame.data[6] = d6;
    frame.data[7] = d7;

    ssize_t n = write(sock, &frame, sizeof(frame));
    if (n != sizeof(frame)) {
        // perror("write(can)");
        return false;// Network is down
    }
    return true;
}
