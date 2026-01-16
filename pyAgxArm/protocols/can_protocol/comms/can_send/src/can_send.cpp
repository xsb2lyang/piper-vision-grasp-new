#include <linux/can.h>
#include <linux/can/raw.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <string>

typedef void (*func_t) (void);
typedef char* string_;

extern "C" {

int open_can(const char* name) {
  std::string idStr(name);
  int sock = ::socket(PF_CAN, SOCK_RAW, CAN_RAW);
  if (sock < 0) {
    perror("socket(PF_CAN)");
    return -1;
  }

  struct ifreq ifr {};
  std::snprintf(ifr.ifr_name, IFNAMSIZ, "%s", idStr.c_str());
  if (ioctl(sock, SIOCGIFINDEX, &ifr) < 0) {
    perror("SIOCGIFINDEX");
    ::close(sock);
    return -1;
  }

  sockaddr_can addr {};
  addr.can_family = AF_CAN;
  addr.can_ifindex = ifr.ifr_ifindex;
  if (bind(sock, reinterpret_cast<sockaddr *>(&addr), sizeof(addr)) < 0) {
    perror("bind(can)");
    ::close(sock);
    return -1;
  }
  return sock;
}

void send_int_data(int sock, int id, 
  uint8_t d0, uint8_t d1, uint8_t d2, uint8_t d3, uint8_t d4, uint8_t d5, uint8_t d6, uint8_t d7){
  struct can_frame frame {};
  frame.can_id = id;
  frame.can_dlc = 8;
  frame.data[0] = static_cast<uint8_t>(d0);
  frame.data[1] = static_cast<uint8_t>(d1);
  frame.data[2] = static_cast<uint8_t>(d2);
  frame.data[3] = static_cast<uint8_t>(d3);
  frame.data[4] = static_cast<uint8_t>(d4);
  frame.data[5] = static_cast<uint8_t>(d5);
  frame.data[6] = static_cast<uint8_t>(d6);
  frame.data[7] = static_cast<uint8_t>(d7);
  if (write(sock, &frame, sizeof(frame)) != static_cast<ssize_t>(sizeof(frame))) {
    perror("write(can)");
  }
}

}// extern "C"
