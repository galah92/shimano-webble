PROGRAM due5000_d.4.5.0.unwrapped.dat

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



=== FUN_00024a40 @ 0x00024a40 size=80 ===

void FUN_00024a40(undefined1 param_1)

{
  undefined4 uStack_44;
  undefined4 uStack_40;
  undefined4 uStack_3c;
  undefined4 local_30;
  undefined4 local_2c;
  undefined4 local_28;
  uint local_24;
  undefined1 auStack_20 [20];

  FUN_000259dc(auStack_20);
  if (*DAT_00024c18 == '\0') {
    FUN_00024f98(param_1,DAT_00024dd8,0x3a);
  }
  else {
    local_24 = (uint)*DAT_00024d8c;
    local_28 = 2;
    local_2c = 0;
    local_30 = DAT_00024dd8;
    FUN_00012e54(&uStack_44,auStack_20,0x14);
    FUN_000256e8(param_1,uStack_44,uStack_40,uStack_3c);
  }
  return;
}



=== FUN_00024a94 @ 0x00024a94 size=98 ===

void FUN_00024a94(undefined1 param_1)

{
  undefined4 uStack_54;
  undefined4 uStack_50;
  undefined4 uStack_4c;
  undefined4 local_40;
  undefined4 local_3c;
  undefined4 local_38;
  uint local_34;
  undefined4 local_30;
  uint local_2c;
  undefined4 local_28;
  uint local_24;
  undefined1 auStack_20 [20];

  FUN_000259dc(auStack_20);
  local_24 = (uint)DAT_00024ddc[2];
  local_28 = 6;
  local_2c = (uint)DAT_00024ddc[1];
  local_30 = 4;
  local_34 = (uint)*DAT_00024ddc;
  local_38 = 2;
  local_3c = 0;
  local_40 = DAT_00024de0;
  FUN_00012e54(&uStack_54,auStack_20,0x14);
  FUN_000258b4(param_1,uStack_54,uStack_50,uStack_4c);
  return;
}



=== FUN_0002721c @ 0x0002721c size=500 ===

uint FUN_0002721c(undefined4 param_1,int param_2)

{
  byte bVar1;
  bool bVar2;
  int iVar3;
  byte bVar4;
  undefined4 uStack_64;
  undefined4 uStack_60;
  undefined4 uStack_5c;
  undefined4 uStack_50;
  undefined4 uStack_4c;
  undefined4 uStack_48;
  undefined4 uStack_44;
  undefined4 uStack_40;
  uint uStack_3c;
  uint uStack_38;
  undefined1 auStack_34 [24];
  undefined4 uStack_1c;
  int iStack_18;

  uStack_1c = param_1;
  iStack_18 = param_2;
  FUN_000259dc(auStack_34);
  bVar4 = *(byte *)(iStack_18 + 4);
  bVar1 = *(byte *)(iStack_18 + 5);
  if (bVar4 == 1) {
    *DAT_00027424 = 1;
    *DAT_00027428 = bVar1;
    *DAT_0002742c = 0;
    uStack_3c = (uint)bVar1;
    uStack_40 = 3;
    uStack_44 = 1;
    uStack_48 = 2;
    uStack_4c = 0;
    uStack_50 = DAT_00027540;
    FUN_00012e54(&uStack_64,auStack_34,0x14);
    uStack_38 = FUN_0002563a(0x3f,uStack_64,uStack_60,uStack_5c);
  }
  else if ((bVar4 == 4) || (bVar4 == 5)) {
    *DAT_00027424 = bVar4;
    *DAT_00027428 = bVar1;
    uStack_38 = 0;
    *DAT_0002742c = 0;
  }
  else if (bVar4 == 0) {
    *DAT_00027544 = 0;
    *DAT_00027424 = 0;
    FUN_000259f4(0);
    FUN_00025a48(0);
    uStack_3c = (uint)bVar1;
    uStack_40 = 3;
    uStack_44 = 0;
    uStack_48 = 2;
    uStack_4c = 0;
    uStack_50 = DAT_00027540;
    FUN_00012e54(&uStack_64,auStack_34,0x14);
    FUN_0002563a(0x3f,uStack_64,uStack_60,uStack_5c);
    uStack_3c = (uint)bVar1;
    uStack_40 = 3;
    uStack_44 = 0;
    uStack_48 = 2;
    uStack_4c = 0;
    uStack_50 = DAT_00027638;
    FUN_00012e54(&uStack_64,auStack_34,0x14);
    FUN_0002563a(bVar1,uStack_64,uStack_60,uStack_5c);
    FUN_0001c33c();
    uStack_38 = 0;
    bVar2 = (bool)isCurrentModePrivileged();
    if (bVar2) {
      uStack_38 = isIRQinterruptsEnabled();
    }
    disableIRQinterrupts();
    for (bVar4 = 0; bVar4 < 0x20; bVar4 = bVar4 + 1) {
      *(undefined1 *)(DAT_000275b0 + (uint)bVar4) = 0;
    }
    uStack_4c = 0;
    uStack_50 = DAT_000275b4;
    FUN_00012e54(&uStack_64,auStack_34,0x14);
    FUN_000255c4(0x3f,uStack_64,uStack_60,uStack_5c);
    *DAT_0002763c = 2;
    *DAT_00027640 = 0xc;
    iVar3 = FUN_000277c0();
    if (iVar3 == 1) {
      if (*DAT_00027644 == '\x01') {
        FUN_00027b28(1);
      }
      else {
        FUN_00027b28(0);
      }
    }
    else {
      FUN_00027cc8(0xc);
    }
    bVar2 = (bool)isCurrentModePrivileged();
    if (bVar2) {
      enableIRQinterrupts((uStack_38 & 1) == 1);
    }
  }
  else if (bVar4 == 2) {
    uStack_3c = (uint)bVar1;
    uStack_40 = 3;
    uStack_44 = 2;
    uStack_48 = 2;
    uStack_4c = 0;
    uStack_50 = DAT_00027638;
    FUN_00012e54(&uStack_64,auStack_34,0x14);
    uStack_38 = FUN_0002563a(bVar1,uStack_64,uStack_60,uStack_5c);
  }
  else {
    uStack_38 = (uint)bVar4;
    if (uStack_38 == 3) {
      uStack_3c = (uint)bVar1;
      uStack_40 = 3;
      uStack_44 = 3;
      uStack_48 = 2;
      uStack_4c = 0;
      uStack_50 = DAT_00027638;
      FUN_00012e54(&uStack_64,auStack_34,0x14);
      uStack_38 = FUN_0002563a(bVar1,uStack_64,uStack_60,uStack_5c);
    }
  }
  return uStack_38;
}



=== FUN_00027430 @ 0x00027430 size=268 ===

void FUN_00027430(undefined4 param_1,int param_2)

{
  byte *pbVar1;
  byte *pbVar2;
  byte *pbVar3;
  undefined4 uStack_5c;
  undefined4 uStack_58;
  undefined4 uStack_54;
  undefined4 uStack_48;
  undefined4 uStack_44;
  undefined4 uStack_40;
  uint uStack_3c;
  undefined4 uStack_38;
  uint uStack_34;
  ushort uStack_30;
  undefined1 auStack_2c [20];
  undefined4 uStack_18;

  uStack_18 = param_1;
  FUN_000259dc(auStack_2c);
  pbVar2 = DAT_0002770c;
  if (*DAT_0002770c != 0) {
    uStack_30 = FUN_0002c25a(param_2 + 2,2);
    if (*pbVar2 == 1) {
      if (*(ushort *)(DAT_00027714 + (uint)*DAT_00027710 * 2) == uStack_30) {
        *DAT_00027710 = *DAT_00027710 + 1;
      }
    }
    else if (*pbVar2 == 4) {
      if (*(ushort *)(DAT_00027718 + (uint)*DAT_00027710 * 2) == uStack_30) {
        *DAT_00027710 = *DAT_00027710 + 1;
      }
    }
    else if (*(ushort *)(DAT_0002771c + (uint)*DAT_00027710 * 2) == uStack_30) {
      *DAT_00027710 = *DAT_00027710 + 1;
    }
    pbVar3 = DAT_00027710;
    pbVar1 = DAT_00027544;
    if (4 < *DAT_00027710) {
      *DAT_00027544 = *pbVar2;
      *pbVar3 = 0;
      FUN_00025a48(1);
      *DAT_00027790 = 0;
      *DAT_00027794 = 0;
      FUN_000279cc();
      pbVar3 = DAT_00027798;
      uStack_34 = (uint)*DAT_00027798;
      uStack_38 = 3;
      uStack_3c = (uint)*pbVar1;
      uStack_40 = 2;
      uStack_44 = 0;
      uStack_48 = DAT_00027638;
      FUN_00012e54(&uStack_5c,auStack_2c,0x14);
      FUN_0002563a(*pbVar3,uStack_5c,uStack_58,uStack_54);
      FUN_0001c2dc(*pbVar3,*pbVar1);
    }
    if (*pbVar2 == 1) {
      uStack_3c = (uint)uStack_30;
      uStack_40 = 2;
      uStack_44 = 0;
      uStack_48 = DAT_0002779c;
      FUN_00012e54(&uStack_5c,auStack_2c,0x14);
      FUN_000256e8(0x3f,uStack_5c,uStack_58,uStack_54);
    }
  }
  return;
}
