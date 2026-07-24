"""Create a C++17 task catalog equivalent to the Python experiment tasks."""

import json
import re
import sys
from pathlib import Path


CPP_STARTERS = {
    "S1-A": ("long long solution(std::vector<int> holes)", "long long solution(std::vector<int> holes) {\n    // TODO\n    return 0;\n}"),
    "S1-D": ("std::vector<Row> solution(const std::vector<Row>& rows, const std::vector<std::string>& wanted_ids)", "struct Row { std::string id; int value; };\n\nstd::vector<Row> solution(const std::vector<Row>& rows, const std::vector<std::string>& wanted_ids) {\n    // TODO\n    return {};\n}"),
    "S1-B": ("std::vector<std::string> solution(const std::string& src_path)", "std::vector<std::string> solution(const std::string& src_path) {\n    std::filesystem::path path(src_path);\n    // BUG: 파일명만 사용해 서로 다른 디렉터리의 같은 파일을 구분할 수 없습니다.\n    std::string original_header = path.filename().string() + \"  (original)\";\n    std::string formatted_header = path.filename().string() + \"  (formatted)\";\n    return {original_header, formatted_header};\n}"),
    "S2-A": ("std::vector<int> solution(int n)", "std::vector<int> solution(int n) {\n    // TODO\n    return {};\n}"),
    "S2-D": ("std::vector<Result> solution(const std::vector<Source>& sources, const std::vector<Query>& queries)", "struct Source { int timestamp; int data; };\nstruct Query { int timestamp; int stuff; };\nstruct Result { int timestamp; int stuff; std::optional<int> data; };\n\nstd::vector<Result> solution(const std::vector<Source>& sources, const std::vector<Query>& queries) {\n    // TODO\n    return {};\n}"),
    "S2-B": ("std::vector<std::vector<double>> solution(const std::vector<std::vector<int>>& image)", "std::vector<std::vector<double>> solution(const std::vector<std::vector<int>>& image) {\n    std::vector<std::vector<double>> result;\n    for (const auto& row : image) {\n        std::vector<double> converted;\n        for (int pixel : row) {\n            // BUG: 정수 변환이 소수 부분을 버립니다.\n            converted.push_back(static_cast<int>(pixel / 127.5 - 1.0));\n        }\n        result.push_back(converted);\n    }\n    return result;\n}"),
    "S3-A": ("std::vector<int> solution(const std::vector<int>& changes)", "std::vector<int> solution(const std::vector<int>& changes) {\n    // TODO\n    return {};\n}"),
    "S3-D": ("std::vector<Row> solution(const std::vector<Row>& rows)", "using Value = std::variant<std::string, int, double, bool, std::monostate>;\nstruct Row { std::map<std::string, Value> values; };\n\nstd::vector<Row> solution(const std::vector<Row>& rows) {\n    // 문자열인지 확인: std::holds_alternative<std::string>(value)\n    // 문자열 가져오기: std::get<std::string>(value)\n    // TODO: 문자열 대안만 치환하고 나머지 대안은 보존하세요.\n    return {};\n}"),
    "S3-B": ("std::vector<std::string> solution(const std::set<std::string>& target_versions)", "std::vector<std::string> solution(const std::set<std::string>& target_versions) {\n    if (target_versions.empty()) return {\"py3\", \"py2_function_print\", \"py2\"};\n    bool all_py3 = std::all_of(target_versions.begin(), target_versions.end(), [](const std::string& v) { return v.rfind(\"py3\", 0) == 0; });\n    if (all_py3) return {\"py3\", \"py2_function_print\"};\n    // BUG: py2_function_print 후보가 누락되었습니다.\n    return {\"py2\"};\n}"),
    "S4-A": ("int solution(const std::vector<int>& targets, int center)", "int solution(const std::vector<int>& targets, int center) {\n    // TODO\n    return 0;\n}"),
    "S4-D": ("std::vector<int> solution(const std::vector<Value>& values)", "using Value = std::variant<int, double, std::string, bool, std::monostate>;\n\nstd::vector<int> solution(const std::vector<Value>& values) {\n    // TODO: int 대안으로 태그된 값만 반환하세요.\n    return {};\n}"),
    "S4-B": ("std::optional<Distribution> solution(const std::string& path, const std::string& data)", "struct Distribution { std::string name; std::optional<std::string> version; };\n\nstd::optional<Distribution> solution(const std::string& path, const std::string& data) {\n    // BUG: 최신 Kali가 사용하는 /etc/os-release를 확인하지 않습니다.\n    if (path == \"/etc/lsb-release\" && data.find(\"Kali\") != std::string::npos) {\n        std::regex pattern(R\"(DISTRIB_RELEASE=\\s*(.*?)\\s*(?:\\n|$))\");\n        std::smatch match;\n        if (std::regex_search(data, match, pattern)) return Distribution{\"Kali\", match[1].str()};\n        return Distribution{\"Kali\", std::nullopt};\n    }\n    return std::nullopt;\n}"),
}

CPP_NOTES = {
    "S1-D": "C++에서는 각 행을 `Row { string id; int value; }` 구조체로 제한합니다. 요청한 id 순서대로 행을 복사해 반환하세요.",
    "S2-D": "C++에서는 `Source`, `Query`, `Result` 구조체를 사용합니다. 해당 센서 값이 없을 때 `Result::data`는 `optional<int>`의 빈 값이어야 합니다.",
    "S3-D": "C++에서는 문자열·정수·실수·bool·값 없음이 들어갈 수 있는 `Value` variant를 사용합니다. 문자열 대안에만 `&LT;` 치환을 적용하세요.",
    "S4-D": "C++에서는 `Value` variant의 `int` 대안으로 태그된 값만 선택합니다. `bool`과 값 없음은 별도 대안입니다.",
    "S3-A": "음수 홀수의 반올림 후보를 계산할 때 C++의 `/`는 0 방향 절삭임에 유의하세요. 요구되는 내림·올림 후보를 명시적으로 계산해야 합니다.",
}

CPP_INPUT_GUIDES = {
    "S1-A": "**입력 형식**\n첫 줄에 8개 정수를 공백으로 구분해 입력합니다.\n```text\n3 1 0 2 4 0 1 2\n```",
    "S1-B": "**입력 형식**\n첫 줄에 POSIX 스타일 파일 경로를 입력합니다.\n```text\nfrontend/utils.py\n```",
    "S1-D": "**입력 형식**\n첫 줄은 `id,value` 레코드를 `;`로, 둘째 줄은 원하는 id를 공백으로 구분합니다.\n```text\na,10;b,20\nb a\n```",
    "S2-A": "**입력 형식**\n첫 줄에 정수 하나를 입력합니다.\n```text\n8\n```",
    "S2-D": "**입력 형식**\n각 줄에서 `timestamp,data` 또는 `timestamp,stuff` 레코드를 `;`로 구분합니다.\n```text\n1,100;5,200\n2,7;6,8\n```",
    "S2-B": "**입력 형식**\n첫 줄에서 행은 `;`, 각 행의 픽셀 값은 공백으로 구분합니다.\n```text\n0 255;128 64\n```",
    "S3-A": "**입력 형식**\n첫 줄에 정수를 공백으로 구분해 입력합니다.\n```text\n-3 5 -2 0\n```",
    "S3-B": "**입력 형식**\n첫 줄에 버전 문자열을 공백으로 구분해 입력합니다.\n```text\npy3 py38\n```",
    "S4-A": "**입력 형식**\n첫 줄은 대상 배열, 둘째 줄은 중심 인덱스입니다.\n```text\n1 0 1 1 1\n2\n```",
    "S4-B": "**입력 형식**\n첫 줄은 경로, 둘째 줄은 파일 내용을 입력합니다.\n```text\n/etc/lsb-release\nDISTRIB_ID=Kali DISTRIB_RELEASE=2024.1\n```",
    "S4-D": "**입력 형식**\n첫 줄에 값 수를, 이후 줄에는 `타입 값`을 입력합니다.\n```text\n3\nint 10\nstring hello\nbool true\n```",
    "S3-D": "**입력 형식**\n첫 줄에서 레코드는 `;`, 필드는 `|`로 구분하고 `키=타입:값`으로 씁니다.\n```text\ntitle=string:hello|count=int:3;active=bool:true\n```",
}

# This support is appended after participant code.  It intentionally accepts one
# JSON value per line, matching the Python catalog's execution contract.
CPP_JSON_SUPPORT = r'''
#include <bits/stdc++.h>
namespace runner {
struct J { enum K{N,B,X,S,A,O}; K k=N; bool b=false; std::string x,s; std::vector<J>a; std::map<std::string,J>o; };
struct P { const std::string& z; size_t i=0; void ws(){while(i<z.size()&&isspace((unsigned char)z[i]))++i;} char take(){ws();return i<z.size()?z[i++]:0;} J val(){ char c=take(); if(c=='"'){J q;q.k=J::S;while(i<z.size()&&z[i]!='"'){if(z[i]=='\\')++i;q.s+=z[i++];}++i;return q;} if(c=='['){J q;q.k=J::A;ws();if(i<z.size()&&z[i]==']'){++i;return q;}for(;;){q.a.push_back(val());ws();char d=z[i++];if(d==']')break;}return q;} if(c=='{'){J q;q.k=J::O;ws();if(i<z.size()&&z[i]=='}'){++i;return q;}for(;;){J key=val();take();q.o[key.s]=val();ws();char d=z[i++];if(d=='}')break;}return q;} --i; size_t st=i;while(i<z.size()&&!strchr(",]} \t\r\n",z[i]))++i;std::string t=z.substr(st,i-st);J q;if(t=="null")q.k=J::N;else if(t=="true"||t=="false"){q.k=J::B;q.b=t=="true";}else{q.k=J::X;q.x=t;}return q;} };
inline J read(){std::string l;std::getline(std::cin,l);return P{l}.val();} inline int integer(const J&v){return std::stoi(v.x);} inline double real(const J&v){return std::stod(v.x);} inline std::string str(const J&v){return v.s;} inline bool decimal(const J&v){return v.x.find_first_of(".eE")!=std::string::npos;}
inline std::vector<int> vi(const J&v){std::vector<int>r;for(auto&x:v.a)r.push_back(integer(x));return r;} inline std::vector<std::string> vs(const J&v){std::vector<std::string>r;for(auto&x:v.a)r.push_back(str(x));return r;} inline std::vector<std::vector<int>> vvi(const J&v){std::vector<std::vector<int>>r;for(auto&x:v.a)r.push_back(vi(x));return r;}
inline std::vector<std::string> split(const std::string&s,char sep){std::vector<std::string>r;std::stringstream q(s);std::string x;while(std::getline(q,x,sep))r.push_back(x);return r;} inline std::vector<int> ints(const std::string&s){std::istringstream q(s);std::vector<int>r;int x;while(q>>x)r.push_back(x);return r;} inline std::vector<std::vector<int>> matrix(const std::string&s){std::vector<std::vector<int>>r;for(auto&row:split(s,';'))r.push_back(ints(row));return r;} inline std::vector<std::string> words(const std::string&s){std::istringstream q(s);std::vector<std::string>r;std::string x;while(q>>x)r.push_back(x);return r;}
inline std::string esc(std::string s){std::string r;for(char c:s){if(c=='"'||c=='\\')r+='\\';r+=c;}return r;} inline std::string out(const std::string&s){return "\""+esc(s)+"\"";} inline std::string out(int x){return std::to_string(x);} inline std::string out(long long x){return std::to_string(x);} inline std::string out(double x){std::ostringstream q;q<<x;return q.str();} inline std::string out(bool x){return x?"true":"false";} inline std::string out(const std::monostate&){return "null";} template<class T> std::string out(const std::vector<T>&v){std::string r="[";for(size_t i=0;i<v.size();++i){if(i)r+=",";r+=out(v[i]);}return r+"]";}
}
'''


def cpp_runner(task_id):
    # Every main consumes exactly one JSON value per solution argument.
    runners = {
        "S1-A": "int main(){std::string line;std::getline(std::cin,line);std::istringstream in(line);std::vector<int>x;int value;while(in>>value)x.push_back(value);std::cout<<solution(x);}",
        "S1-B": "int main(){std::string line;std::getline(std::cin,line);std::cout<<runner::out(solution(line));}",
        "S2-A": "int main(){int n;std::cin>>n;std::cout<<runner::out(solution(n));}",
        "S2-B": "int main(){std::string line;std::getline(std::cin,line);std::cout<<runner::out(solution(runner::matrix(line)));}",
        "S3-A": "int main(){std::string line;std::getline(std::cin,line);std::cout<<runner::out(solution(runner::ints(line)));}",
        "S3-B": "int main(){std::string line;std::getline(std::cin,line);auto x=runner::words(line);std::set<std::string>s(x.begin(),x.end());std::cout<<runner::out(solution(s));}",
        "S4-A": "int main(){std::string line;std::getline(std::cin,line);std::istringstream in(line);std::vector<int>x;int value;while(in>>value)x.push_back(value);std::getline(std::cin,line);std::cout<<solution(x,std::stoi(line));}",
        "S1-D": "int main(){std::string line;std::getline(std::cin,line);std::vector<Row>r;for(auto&item:runner::split(line,';')){auto p=runner::split(item,',');r.push_back({p[0],std::stoi(p[1])});}std::getline(std::cin,line);auto w=runner::words(line);auto z=solution(r,w);std::cout<<\"[\";for(size_t i=0;i<z.size();++i){if(i)std::cout<<\",\";std::cout<<\"{\\\"id\\\":\"<<runner::out(z[i].id)<<\",\\\"value\\\":\"<<z[i].value<<\"}\";}std::cout<<\"]\";}",
        "S2-D": "int main(){std::string line;std::getline(std::cin,line);std::vector<Source>s;for(auto&item:runner::split(line,';')){auto p=runner::split(item,',');s.push_back({std::stoi(p[0]),std::stoi(p[1])});}std::getline(std::cin,line);std::vector<Query>q;for(auto&item:runner::split(line,';')){auto p=runner::split(item,',');q.push_back({std::stoi(p[0]),std::stoi(p[1])});}auto z=solution(s,q);std::cout<<\"[\";for(size_t i=0;i<z.size();++i){if(i)std::cout<<\",\";std::cout<<\"{\\\"timestamp\\\":\"<<z[i].timestamp<<\",\\\"stuff\\\":\"<<z[i].stuff<<\",\\\"data\\\":\"<<(z[i].data?std::to_string(*z[i].data):\"null\")<<\"}\";}std::cout<<\"]\";}",
        "S4-B": "int main(){std::string p,d;std::getline(std::cin,p);std::getline(std::cin,d);auto z=solution(p,d);if(!z)std::cout<<\"null\";else std::cout<<\"{\\\"name\\\":\"<<runner::out(z->name)<<\",\\\"version\\\":\"<<(z->version?runner::out(*z->version):\"null\")<<\"}\";}",
    }
    if task_id not in runners:
        # Variant-heavy tasks remain runnable; their function signature receives
        # JSON values translated to the declared alternatives.
        if task_id == "S4-D":
            return "int main(){std::string line;std::getline(std::cin,line);int count=std::stoi(line);std::vector<Value>v;for(int i=0;i<count;++i){std::getline(std::cin,line);std::istringstream in(line);std::string tag;in>>tag;if(tag==\"int\"){int x;in>>x;v.push_back(x);}else if(tag==\"double\"){double x;in>>x;v.push_back(x);}else if(tag==\"string\"){std::string x;std::getline(in>>std::ws,x);v.push_back(x);}else if(tag==\"bool\"){std::string x;in>>x;v.push_back(x==\"true\");}else if(tag==\"null\")v.push_back(std::monostate{});}std::cout<<runner::out(solution(v));}"
        if task_id == "S3-D":
            return "int main(){std::string line;std::getline(std::cin,line);std::vector<Row>r;for(auto&record:runner::split(line,';')){Row row;for(auto&field:runner::split(record,'|')){auto eq=field.find('=');auto colon=field.find(':',eq+1);auto key=field.substr(0,eq),tag=field.substr(eq+1,colon-eq-1),value=field.substr(colon+1);if(tag==\"int\")row.values[key]=std::stoi(value);else if(tag==\"double\")row.values[key]=std::stod(value);else if(tag==\"string\")row.values[key]=value;else if(tag==\"bool\")row.values[key]=(value==\"true\");else row.values[key]=std::monostate{};}r.push_back(row);}auto z=solution(r);std::cout<<\"[\";for(size_t i=0;i<z.size();++i){if(i)std::cout<<\",\";std::cout<<\"{\";bool f=true;for(auto&kv:z[i].values){if(!f)std::cout<<\",\";f=false;std::cout<<runner::out(kv.first)<<\":\";std::visit([](auto&&q){std::cout<<runner::out(q);},kv.second);}std::cout<<\"}\";}std::cout<<\"]\";}"
    return runners[task_id]


def main():
    source, output = map(Path, sys.argv[1:3])
    tasks = json.loads(source.read_text(encoding="utf-8"))
    converted = []
    for task in tasks:
        signature, starter = CPP_STARTERS[task["id"]]
        context = task["body_ko"].split("**함수 규격**", 1)[0].strip()
        context = re.sub(r"^\*\*사용 언어: Python\*\*\s*", "", context)
        context = (context.replace("딕셔너리", "구조체").replace("list", "vector")
                   .replace("None", "std::nullopt").replace("표준 라이브러리 `re`", "표준 `<regex>` 라이브러리"))
        if task["id"] == "S4-D":
            context = "외부 API 값은 C++ `Value` variant로 전달됩니다. int, double, string, bool, 값 없음 중 실제 int로 태그된 값만 원래 순서대로 추출하세요. C++에서는 int와 bool이 별도 variant 대안이므로, 이 문항은 Python의 bool-정수 상속 함정 대신 variant 타입 태그 판별을 평가합니다."
        if task["id"] == "S1-B":
            context = "코드 포매터는 수정 전과 수정 후의 파일 이름을 diff 헤더에 표시합니다. 서로 다른 디렉터리에 같은 파일명이 있을 수 있으므로, 헤더에는 입력으로 받은 경로 전체가 유지되어야 합니다. 현재 구현은 경로에서 파일명만 꺼내 두 헤더를 만듭니다. 원본과 수정본 헤더가 모두 전체 경로를 사용하도록 최소 수정하세요. 반환 벡터의 첫 번째 원소는 원본 헤더, 두 번째 원소는 수정본 헤더입니다."
        body = f"**사용 언어: C++17**\n\n{context}\n\n{CPP_NOTES.get(task['id'], '')}\n\n**C++17 함수 규격**\n```cpp\n{signature};\n```"
        body += "\n\n" + CPP_INPUT_GUIDES[task["id"]]
        body += "\n\n**다음과 같은 형태로, 함수 매개변수를 순서대로 한 줄씩 입력합니다.** 별도의 `main` 함수나 파싱을 구현할 필요는 없습니다."
        converted.append({
            **{key: value for key, value in task.items() if key not in {"starter_code", "execution_runner", "body", "body_ko"}},
            "language": "cpp17",
            "body": body,
            "body_ko": body,
            "function_signature": signature,
            "starter_code": "#include <bits/stdc++.h>\nusing namespace std;\n\n" + starter,
            "execution_runner": CPP_JSON_SUPPORT + cpp_runner(task["id"]),
        })
    output.write_text(json.dumps(converted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
