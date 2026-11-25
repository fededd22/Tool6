from ..ANSI_COLORS import ANSI; C = ANSI()
from ..MODULES import IMPORT; M = IMPORT()

C_Line = f"{C.CC}{'_' * 61}"

TAG_TEXT = "by moon"


# ---------------- Find Launcher Activity Class ----------------
def Find_Launcher_Activity(manifest_path, Package_Name):

    content = open(manifest_path, 'r', encoding='utf-8', errors='ignore').read()

    # ---------------- Scan Every <activity> Block ----------------
    # ملاحظة: وسوم <activity .../> ذاتية الإغلاق (بدون intent-filter) لا تحتوي
    # إغلاقاً منفصلاً </activity>؛ يجب مطابقتها أولاً وإلا امتد البحث الجشع
    # عبرها ليدمجها خطأً مع أول نشاط بعدها.
    activity_pattern = r'<activity\b[^>]*?/>|<activity\b[^>]*>(?:(?!</activity>).)*?</activity>'

    for activity_match in M.re.finditer(activity_pattern, content, M.re.S):

        block = activity_match[0]

        if not (M.re.search(r'android:name="android\.intent\.action\.MAIN"', block)
                and M.re.search(r'android:name="android\.intent\.category\.LAUNCHER"', block)):
            continue

        name_match = M.re.search(r'<activity\b[^>]*\sandroid:name="([^"]+)"', block)

        if not name_match:
            continue

        class_name = name_match[1]

        # ---------------- Resolve Relative Class Name ----------------
        if class_name.startswith('.'):
            class_name = f"{Package_Name}{class_name}"
        elif '.' not in class_name:
            class_name = f"{Package_Name}.{class_name}"

        return class_name

    return None


# ---------------- Find Smali File for a Class ----------------
def Find_Smali_File(smali_folders, class_name):

    rel_path = class_name.replace('.', '/') + '.smali'

    for folder in smali_folders:
        candidate = M.os.path.join(folder, rel_path)

        if M.os.path.isfile(candidate):
            return candidate

    return None


# ---------------- Patch "by moon" Branding ----------------
def Patch_Branding(decompile_dir, smali_folders, manifest_path, Package_Name):

    print(
        f"\n{C_Line}\n\n"
        f"\n{C.X}{C.C} Branding Patch ( by moon )..."
    )

    class_name = Find_Launcher_Activity(manifest_path, Package_Name)

    if not class_name:
        print(f"\n{C.WARN} Could not find Launcher Activity in Manifest, Skipping Branding Patch.\n")
        return

    smali_path = Find_Smali_File(smali_folders, class_name)

    if not smali_path:
        print(f"\n{C.WARN} Could not find Smali File for {C.Y}'{class_name}'{C.C}, Skipping Branding Patch.\n")
        return

    content = open(smali_path, 'r', encoding='utf-8', errors='ignore').read()

    method_match = M.re.search(
        r'(\.method\s+[^\n]*\bonCreate\(Landroid/os/Bundle;\)V\n)(.*?\n)(\.end method)',
        content, M.re.S
    )

    # ---------------- Class Has No onCreate of Its Own ----------------
    # شائع جداً مع تطبيقات Flutter: الصنف اللانشر فارغ تماماً (يرث onCreate
    # بالكامل من صنفه الأب مثل FlutterActivity دون أي دالة خاصة به).
    # الحل الأسلم: إضافة دالة onCreate جديدة بالكامل تستدعي super ثم تعرض
    # الإشعار، بدل محاولة تعديل دالة قد تكون في مكتبة خارجية معقدة.
    if not method_match:
        super_class_match = M.re.search(r'\.super\s+(L[^;]+;)', content)

        if not super_class_match:
            print(f"\n{C.WARN} Could not read .super in {C.Y}'{M.os.path.basename(smali_path)}'{C.C}, Skipping Branding Patch.\n")
            return

        super_class = super_class_match[1]

        new_method = (
            f"\n.method protected onCreate(Landroid/os/Bundle;)V\n"
            f"    .locals 2\n\n"
            f"    invoke-super {{p0, p1}}, {super_class}->onCreate(Landroid/os/Bundle;)V\n\n"
            f"    const-string v0, \"{TAG_TEXT}\"\n\n"
            f"    const/4 v1, 0x0\n\n"
            f"    invoke-static {{p0, v0, v1}}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;\n\n"
            f"    move-result-object v0\n\n"
            f"    invoke-virtual {{v0}}, Landroid/widget/Toast;->show()V\n\n"
            f"    return-void\n"
            f".end method\n"
        )

        open(smali_path, 'w', encoding='utf-8', errors='ignore').write(content.rstrip('\n') + '\n' + new_method)

        print(
            f"\n{C.S} Branding Tag {C.E} {C.OG}➸❥ {C.P}'{C.G}{TAG_TEXT}{C.P}' {C.OG}➸❥ {C.Y}{class_name} {C.P}( New onCreate ){C.G} ✔\n"
        )
        return

    header, body, footer = method_match[1], method_match[2], method_match[3]

    locals_match = M.re.search(r'\.locals (\d+)', body)

    if not locals_match:
        print(f"\n{C.WARN} Could not read .locals in {C.Y}'{M.os.path.basename(smali_path)}'{C.C}, Skipping Branding Patch.\n")
        return

    locals_count = int(locals_match[1])

    # نستخدم سجلّين جديدين لم يُستخدَما من قبل (بزيادة .locals)، فلا تصادم مطلقاً
    # مع أي سجلّ آخر مستخدَم أصلاً داخل الدالة.
    reg_toast, reg_dur = f"v{locals_count}", f"v{locals_count + 1}"

    toast_snippet = (
        f"\n\n    const-string {reg_toast}, \"{TAG_TEXT}\"\n\n"
        f"    const/4 {reg_dur}, 0x0\n\n"
        f"    invoke-static {{p0, {reg_toast}, {reg_dur}}}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;\n\n"
        f"    move-result-object {reg_toast}\n\n"
        f"    invoke-virtual {{{reg_toast}}}, Landroid/widget/Toast;->show()V\n"
    )

    new_body = M.re.sub(r'\.locals \d+', f'.locals {locals_count + 2}', body, count=1)

    # ---------------- Insert Right After super.onCreate(...) Call ----------------
    super_match = M.re.search(r'invoke-super \{p0, p1\}, L[^;]+;->onCreate\(Landroid/os/Bundle;\)V\n', new_body)

    if super_match:
        insert_at = super_match.end()
        new_body = new_body[:insert_at] + toast_snippet + new_body[insert_at:]
    else:
        # لا يوجد استدعاء super صريح (نادر)؛ نضيف السطر في بداية الدالة كحل بديل
        new_body = toast_snippet + new_body

    new_method = header + new_body + footer

    content = content[:method_match.start()] + new_method + content[method_match.end():]

    open(smali_path, 'w', encoding='utf-8', errors='ignore').write(content)

    print(
        f"\n{C.S} Branding Tag {C.E} {C.OG}➸❥ {C.P}'{C.G}{TAG_TEXT}{C.P}' {C.OG}➸❥ {C.Y}{class_name}{C.G} ✔\n"
    )
