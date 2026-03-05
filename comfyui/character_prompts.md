# 角色盲盒提示词模板

## 风格提示词（固定）
```
数字水粉厚涂, 厚涂插画, 哑光质感, 纯2D手绘,
无3D感, 无光泽, 无油腻感,
digital gouache painting, impasto thick paint texture,
matte painterly surface, no glossy material, no wet shine,
opaque layered brushstrokes, rich pigment body,
HAIR: matte velvet powdery finish, chalky dry-brush strokes,
soft diffused rim light on hair, no reflective streaks,
hard edge on clothing silhouette, soft edge on hair,
warm orange-gold key light, cool blue-teal shadows,
strong color temperature contrast, soft halation,
intricate gold filigree on jewelry,
fine embroidery on collar cuffs and hem only,
dark background #1a1a2e, seamless character edge
```

## 视角提示词（固定）
```
isometric game sprite, 45 degree diagonal from upper-left,
camera 30 degree elevation looking down,
facing lower-right, full body visible, centered,
orthographic isometric view
```

## 具体角色提示词（可替换）

### 示例1：小仙女
```
tiny female immortal, flowing white-ivory hanfu,
translucent gossamer sleeves, soft pink inner robe,
small gold crown, cherry blossom hairpin,
holding glowing lotus lantern,
gentle curious expression, rosy cheeks, bright open eyes,
pink + ivory + soft gold palette
```

### 示例2：武侠角色
```
tiny male warrior, traditional chinese martial arts attire,
flowing black robe with gold trim, white inner garment,
high topknot hairstyle with red ribbon,
holding a sword, confident stance,
determined expression, focused eyes,
black + gold + red color palette
```

### 示例3：奇幻角色
```
tiny elven character, pointed ears, flowing green robes,
nature-inspired accessories, holding a staff with crystal,
calm wise expression, forest-themed attire,
green + brown + gold color palette
```

## 使用方法
1. 保持风格提示词和视角提示词不变
2. 替换具体角色提示词部分
3. 将三部分合并成一个完整的提示词
4. 使用 `z_image_blindbox.json` 工作流生成图像