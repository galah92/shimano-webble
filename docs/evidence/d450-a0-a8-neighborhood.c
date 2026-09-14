PROGRAM due5000_d.4.5.0.unwrapped.dat

=== FUN_000250a4 @ 0x000250a4 size=84 ===

undefined4 FUN_000250a4(undefined1 param_1,int param_2,undefined4 param_3,undefined4 param_4)

{
  if (*(char *)(param_2 + 4) == '\0') {
    if (*DAT_00025364 == '\0') {
      FUN_00024f98(param_1,DAT_00025414,0x3a);
    }
    else {
      *DAT_00025368 = param_1;
      *DAT_0002536c = 0;
      *DAT_00025370 = 0x39000;
      *DAT_00025374 = 0;
      *DAT_00025378 = 1;
    }
  }
  else {
    FUN_000247e0(param_1,param_2);
  }
  return param_4;
}



=== FUN_00025100 @ 0x00025100 size=80 ===

void FUN_00025100(undefined1 param_1,int param_2)

{
  undefined2 *puVar1;
  undefined2 uVar2;

  if (*DAT_00025364 == '\0') {
    FUN_00024f98(param_1,DAT_00025498,0x3a);
  }
  else {
    *DAT_00025368 = param_1;
    puVar1 = DAT_00025370;
    *(undefined1 *)(DAT_00025370 + 1) = *(undefined1 *)(param_2 + 4);
    uVar2 = FUN_0002c25a(param_2 + 2,3);
    *puVar1 = uVar2;
    uVar2 = FUN_0002c25a(param_2 + 2,5);
    *DAT_00025418 = uVar2;
    *DAT_00025374 = 0;
    *DAT_00025378 = 2;
  }
  return;
}



=== FUN_000252a8 @ 0x000252a8 size=176 ===

void FUN_000252a8(undefined1 param_1,int param_2,undefined4 param_3,undefined4 param_4)

{
  undefined4 uVar1;
  undefined4 uStack_54;
  undefined4 uStack_50;
  undefined4 uStack_4c;
  undefined4 uStack_40;
  undefined4 uStack_3c;
  undefined4 uStack_38;
  undefined4 uStack_34;
  char cStack_30;
  char cStack_2f;
  undefined1 auStack_2c [2];
  undefined1 auStack_2a [3];
  undefined1 auStack_27 [15];
  undefined4 uStack_18;

  cStack_2f = '\x01';
  uStack_18 = param_4;
  FUN_000259dc(auStack_2c);
  uVar1 = DAT_00025594;
  if (((*DAT_00025364 == '\x04') || (*DAT_00025364 == '\x05')) &&
     (cStack_30 = *(char *)(param_2 + 4), cStack_30 == '\0')) {
    FUN_0002a9b6(DAT_00025594,param_2 + 5,5);
    *DAT_00025598 = 1;
    auStack_2c[0] = 8;
    FUN_0002c21a(auStack_2a,DAT_0002559c,0,8);
    FUN_0002c2bc(auStack_2a,2,cStack_30);
    FUN_0002a9b6(auStack_27,uVar1,5);
    FUN_00025552(param_1,auStack_2c);
    cStack_2f = '\0';
  }
  if (cStack_2f == '\x01') {
    uStack_34 = 0x3a;
    uStack_38 = 2;
    uStack_3c = 1;
    uStack_40 = DAT_0002559c;
    FUN_00012e54(&uStack_54,auStack_2c,0x14);
    FUN_000256e8(param_1,uStack_54,uStack_50,uStack_4c);
  }
  return;
}



=== FUN_0002537c @ 0x0002537c size=150 ===

void FUN_0002537c(uint param_1,int param_2)

{
  bool bVar1;
  char *pcVar2;
  undefined4 uVar3;
  int iVar4;
  undefined4 uStack_54;
  undefined4 uStack_50;
  undefined4 uStack_4c;
  undefined4 uStack_40;
  undefined4 uStack_3c;
  undefined4 uStack_38;
  undefined4 uStack_34;
  undefined1 auStack_30 [2];
  undefined1 auStack_2e [2];
  undefined1 auStack_2c [16];
  uint uStack_1c;
  int iStack_18;

  bVar1 = true;
  uStack_1c = param_1;
  iStack_18 = param_2;
  FUN_000259dc(auStack_30);
  uVar3 = DAT_000255a4;
  pcVar2 = DAT_00025598;
  if (((*DAT_000255a0 == '\x04') || (*DAT_000255a0 == '\x05')) && (*DAT_00025598 == '\x01')) {
    FUN_0002a9b6(DAT_000255a4,iStack_18 + 4,6);
    *pcVar2 = '\0';
    iVar4 = FUN_00025516();
    if (iVar4 == 1) {
      auStack_30[0] = 8;
      FUN_0002c21a(auStack_2e,DAT_000255a8,0,8);
      FUN_0002a9b6(auStack_2c,uVar3,6);
      FUN_00025552(uStack_1c & 0xff,auStack_30);
      bVar1 = false;
    }
  }
  if (bVar1) {
    uStack_34 = 0x3a;
    uStack_38 = 2;
    uStack_3c = 1;
    uStack_40 = DAT_000255a8;
    FUN_00012e54(&uStack_54,auStack_30,0x14);
    FUN_000256e8(uStack_1c & 0xff,uStack_54,uStack_50,uStack_4c);
  }
  return;
}



=== FUN_0002541c @ 0x0002541c size=124 ===

void FUN_0002541c(undefined1 param_1,int param_2)

{
  undefined4 uStack_4c;
  undefined4 uStack_48;
  undefined4 uStack_44;
  undefined4 local_38;
  undefined4 local_34;
  undefined4 local_30;
  undefined4 local_2c;
  undefined1 local_28 [2];
  undefined1 auStack_26 [3];
  undefined1 auStack_23 [15];

  FUN_000259dc(local_28);
  if (*(char *)(param_2 + 4) == '\0') {
    local_28[0] = 8;
    FUN_0002c21a(auStack_26,DAT_000255ac,0,8);
    FUN_0002c2bc(auStack_26,2,0);
    FUN_0002a9b6(auStack_23,DAT_000255b0,5);
    FUN_00025552(param_1,local_28);
  }
  else {
    local_2c = 0x3a;
    local_30 = 2;
    local_34 = 1;
    local_38 = DAT_000255ac;
    FUN_00012e54(&uStack_4c,local_28,0x14);
    FUN_000256e8(param_1,uStack_4c,uStack_48,uStack_44);
  }
  return;
}



=== FUN_000254a4 @ 0x000254a4 size=114 ===

void FUN_000254a4(undefined1 param_1,int param_2)

{
  undefined4 uStack_4c;
  undefined4 uStack_48;
  undefined4 uStack_44;
  undefined4 local_38;
  undefined4 local_34;
  undefined4 local_30;
  undefined4 local_2c;
  undefined1 local_28 [2];
  undefined1 auStack_26 [2];
  undefined1 auStack_24 [16];

  FUN_000259dc(local_28);
  if (*(char *)(param_2 + 4) == '\0') {
    local_28[0] = 8;
    FUN_0002c21a(auStack_26,DAT_000255b4,0,8);
    FUN_0002a9b6(auStack_24,DAT_000255b8,6);
    FUN_00025552(param_1,local_28);
  }
  else {
    local_2c = 0x3a;
    local_30 = 2;
    local_34 = 1;
    local_38 = DAT_000255b4;
    FUN_00012e54(&uStack_4c,local_28,0x14);
    FUN_000256e8(param_1,uStack_4c,uStack_48,uStack_44);
  }
  return;
}
