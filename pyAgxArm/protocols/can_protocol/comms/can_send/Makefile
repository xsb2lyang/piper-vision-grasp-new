# 编译成so还是可执行文件
CUSTOM_COMPILE_OPTIONS = 1
# 可执行文件的名字
ifeq ($(CUSTOM_COMPILE_OPTIONS), 1)
TARGET = libcan_send_cpp.so
endif
ifeq ($(CUSTOM_COMPILE_OPTIONS), 0)
TARGET = can_send_cpp
endif
TARGET := $(addprefix ./,$(TARGET))
# 方便起见一般都会先定义编译器链接器
CC = g++ 
LD = gcc
# 将生成的中间文件放在temp里
BUILD_DIR = temp
# 正则表达式表示目录下所有.c文件，相当于：SRCS = main.c a.c b.c
C_SOURCES = \
$(wildcard ./*.cpp) \
$(wildcard ./src/*.cpp)
# 打印源文件路径
$(warning $(C_SOURCES))

# C文件头文件所在路径
C_INCLUDES = \
-I/usr/include/python3.8
# 编译标志
CFLAGS = -std=c++11
ifeq ($(CUSTOM_COMPILE_OPTIONS), 1)
CFLAGS += -shared -fPIC
endif
# .PHONE伪目标，具体含义百度一下一大堆介绍
.PHONY:all clean

# 要生成的目标文件
all: $(TARGET)
# OBJS表示C_SOURCES中把列表中的.c全部替换为.o，相当于：OBJS = main.o a.o b.o
OBJS = $(addprefix $(BUILD_DIR)/,$(notdir $(patsubst %cpp, %o, $(C_SOURCES))))
OBJECTS = $(addprefix $(BUILD_DIR)/,$(notdir $(C_SOURCES:.cpp=.o)))
vpath %.cpp $(sort $(dir $(C_SOURCES)))
# 第一行依赖关系：冒号后面为依赖的文件，相当于Hello: main.o a.o b.o
# 第二行规则：
# $@表示目标文件，表示规则中的目标文件集。在模式规则中，如果有多个目标，那么，"$@"就是匹配于目标中模式定义的集合
# $^表示所有依赖文件，所有的依赖目标的集合。以空格分隔。如果在依赖目标中有多个重复的，那个这个变量会去除重复的依赖目标，只保留一份。
# $<表示第一个依赖文件,依赖目标中的第一个目标名字。如果依赖目标是以模式（即"%"）定义的，那么"$<"将是符合模式的一系列的文件集。注意，其是一个一个取出来的。
$(TARGET): $(OBJECTS) | $(BUILD_DIR)
	$(CC) $(CFLAGS) $^ -o $@

# 上一句目标文件依赖一大堆.o文件，这句表示所有.o都由相应名字的.c文件自动生成
$(BUILD_DIR)/%.o: %.cpp | $(BUILD_DIR)
	$(CC) -c $(CFLAGS) $(C_INCLUDES) $< -o $@

$(BUILD_DIR):
	mkdir $@
# make clean删除所有.o和目标文件
clean:
	rm -rf $(BUILD_DIR)
rebuild:
	rm -rf $(BUILD_DIR)
	make all -j `cat /proc/cpuinfo | grep processor| wc -l`
