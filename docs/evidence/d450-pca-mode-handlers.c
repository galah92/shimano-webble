PROGRAM due5000_d.4.5.0.unwrapped.dat

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



=== FUN_000275b8 @ 0x000275b8 size=126 ===

void FUN_000275b8(undefined1 param_1,int param_2,undefined4 param_3,undefined4 param_4)

{
  undefined4 *puVar1;
  undefined4 uVar2;
  int iVar3;
  undefined4 uStack_4c;
  undefined4 uStack_48;
  undefined4 uStack_44;
  undefined4 uStack_38;
  undefined4 uStack_34;
  undefined4 uStack_30;
  undefined4 uStack_2c;
  undefined1 auStack_28 [20];
  undefined4 uStack_14;

  uStack_14 = param_4;
  FUN_000259dc(auStack_28);
  puVar1 = DAT_000277ac;
  if (*DAT_000277a8 == '\0') {
    FUN_00024f98(param_1,DAT_000277b0,0x3a);
  }
  else {
    uVar2 = FUN_0002c296(param_2 + 2,2);
    *puVar1 = uVar2;
    FUN_000295d8(0xb,puVar1);
    FUN_0002964e();
    iVar3 = FUN_00029676(0xb);
    if (iVar3 == 0) {
      FUN_00024f98(param_1,DAT_000277b0,0x3a);
    }
    else {
      uStack_2c = *puVar1;
      uStack_30 = 2;
      uStack_34 = 0;
      uStack_38 = DAT_000277b0;
      FUN_00012e54(&uStack_4c,auStack_28,0x14);
      FUN_000257d8(param_1,uStack_4c,uStack_48,uStack_44);
    }
  }
  return;
}
